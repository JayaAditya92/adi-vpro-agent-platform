
import hashlib
from contextlib import asynccontextmanager
from io import BytesIO
from pydantic import BaseModel, Field
from app.rag_service import generate_rag_answer
from app.mcp_agent_api import router as mcp_agent_router
from app.evaluation_dashboard import router as evaluation_dashboard_router
from app.prompt_manager import get_prompt_metadata
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File
)

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from pypdf import PdfReader
from docx import Document as DocxDocument

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database import engine, Base, get_db
from app import models
from app.embedding_service import generate_embedding
from app.agent_graph import run_rag_agent
from app.agentic_tools import run_tool_agent
from app.security_service import moderation_check

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000
    )
class RAGRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000
    )


class ChatRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=1, max_length=2000)


class AgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


# --------------------------------------------------
# SHA-256 helper
# --------------------------------------------------

def calculate_content_hash(content):

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------
# Database initialization and duplicate migration
# --------------------------------------------------

def initialize_database():

    # Enable pgvector
    with engine.begin() as connection:

        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )

    # Create missing tables
    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:

        # Add hash column if it does not exist
        connection.execute(
            text("""
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)
            """)
        )

        # Remove the previous unique index before recalculating
        # all hashes consistently using SHA-256.
        connection.execute(
            text("""
                DROP INDEX IF EXISTS ix_documents_content_hash
            """)
        )

        # Read all documents and their existing chunk counts
        records = connection.execute(
            text("""
                SELECT
                    d.id,
                    d.content,
                    COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks c
                    ON c.document_id = d.id
                GROUP BY d.id, d.content
                ORDER BY d.id
            """)
        ).mappings().all()

        # Group records by SHA-256 content hash
        grouped_documents = {}

        for record in records:

            content_hash = calculate_content_hash(
                record["content"]
            )

            grouped_documents.setdefault(
                content_hash, []
            ).append(record)

        # Recalculate hashes and remove duplicate records
        for content_hash, documents in grouped_documents.items():

            # Keep the document with the most chunks.
            # If tied, retain the lowest document ID.
            documents.sort(
                key=lambda item: (
                    -item["chunk_count"],
                    item["id"]
                )
            )

            keep_document = documents[0]

            # Update the retained document hash
            connection.execute(
                text("""
                    UPDATE documents
                    SET content_hash = :content_hash
                    WHERE id = :document_id
                """),
                {
                    "content_hash": content_hash,
                    "document_id": keep_document["id"]
                }
            )

            # Remove other copies and their chunks
            for duplicate in documents[1:]:

                duplicate_id = duplicate["id"]

                connection.execute(
                    text("""
                        DELETE FROM document_chunks
                        WHERE document_id = :document_id
                    """),
                    {"document_id": duplicate_id}
                )

                connection.execute(
                    text("""
                        DELETE FROM documents
                        WHERE id = :document_id
                    """),
                    {"document_id": duplicate_id}
                )

        # Require every document to have a hash
        connection.execute(
            text("""
                ALTER TABLE documents
                ALTER COLUMN content_hash SET NOT NULL
            """)
        )

        # Enforce uniqueness at database level
        connection.execute(
            text("""
                CREATE UNIQUE INDEX ix_documents_content_hash
                ON documents(content_hash)
            """)
        )


# --------------------------------------------------
# Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    initialize_database()

    yield


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="VPRO Agent Platform",
    description="Agentic AI Chatbot Backend",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(mcp_agent_router)
app.include_router(evaluation_dashboard_router)

# --------------------------------------------------
# React CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# Extract document text
# --------------------------------------------------

def extract_text(filename, content):

    filename = filename.lower()

    if filename.endswith(".pdf"):

        reader = PdfReader(BytesIO(content))

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if filename.endswith(".docx"):

        doc = DocxDocument(BytesIO(content))

        return "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
        )

    if filename.endswith(".txt"):

        return content.decode("utf-8-sig")

    raise ValueError("Unsupported document")


# --------------------------------------------------
# Home API
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Welcome to VPRO Agent Platform",
        "status": "Backend Running"
    }


# --------------------------------------------------
# Database health
# --------------------------------------------------

@app.get("/api/db-health")
def database_health(db: Session = Depends(get_db)):

    db.execute(text("SELECT 1"))

    return {
        "status": "success",
        "message": "PostgreSQL connected successfully"
    }


# --------------------------------------------------
# pgvector health
# --------------------------------------------------

@app.get("/api/vector-health")
def vector_health(db: Session = Depends(get_db)):

    result = db.execute(
        text("""
            SELECT extversion
            FROM pg_extension
            WHERE extname = 'vector'
        """)
    ).scalar_one_or_none()

    if result is None:

        raise HTTPException(
            status_code=500,
            detail="pgvector is not enabled"
        )

    return {
        "status": "success",
        "message": "pgvector is enabled",
        "version": result
    }


# --------------------------------------------------
# Upload document with duplicate prevention
# --------------------------------------------------

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    filename = file.filename or ""

    extension = (
        "." + filename.rsplit(".", 1)[-1].lower()
        if "." in filename else ""
    )

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX and TXT files are allowed"
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB"
        )

    if not content:

        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    try:

        extracted_text = extract_text(filename, content)

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail="Unable to extract document text"
        ) from error

    if not extracted_text.strip():

        raise HTTPException(
            status_code=400,
            detail="No readable text found"
        )

    # Calculate SHA-256 from extracted text
    content_hash = calculate_content_hash(extracted_text)

    # Check existing document
    existing_document = (
        db.query(models.Document)
        .filter(
            models.Document.content_hash == content_hash
        )
        .first()
    )

    if existing_document:

        return {
            "status": "already_exists",
            "message": "This document has already been uploaded",
            "document_id": existing_document.id,
            "filename": existing_document.filename,
            "characters_extracted": len(extracted_text)
        }

    # Create new document
    document = models.Document(
        filename=filename,
        content=extracted_text,
        content_hash=content_hash
    )

    try:

        db.add(document)
        db.commit()
        db.refresh(document)

    except IntegrityError:

        # Another request may have uploaded the same document
        # at the same time. The unique index prevents duplication.
        db.rollback()

        existing_document = (
            db.query(models.Document)
            .filter(
                models.Document.content_hash == content_hash
            )
            .first()
        )

        if existing_document:

            return {
                "status": "already_exists",
                "message": "This document has already been uploaded",
                "document_id": existing_document.id,
                "filename": existing_document.filename,
                "characters_extracted": len(extracted_text)
            }

        raise HTTPException(
            status_code=500,
            detail="Unable to save document"
        )

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to save document"
        ) from error

    return {
        "status": "success",
        "document_id": document.id,
        "filename": document.filename,
        "characters_extracted": len(extracted_text)
    }


# --------------------------------------------------
# List documents
# --------------------------------------------------

@app.get("/api/documents")
def get_documents(db: Session = Depends(get_db)):

    documents = (
        db.query(models.Document)
        .order_by(models.Document.id.desc())
        .all()
    )

    chunk_counts = dict(
        db.query(
            models.DocumentChunk.document_id,
            func.count(models.DocumentChunk.id)
        )
        .group_by(models.DocumentChunk.document_id)
        .all()
    )

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "characters": len(doc.content),
            "created_at": doc.created_at,
            "chunks": chunk_counts.get(doc.id, 0)
        }
        for doc in documents
    ]


# --------------------------------------------------
# Generate chunks and embeddings
# --------------------------------------------------

@app.post("/api/documents/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db)
):

    document = db.get(models.Document, document_id)

    if document is None:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(document.content)

    if not chunks:

        raise HTTPException(
            status_code=400,
            detail="No text available for chunking"
        )

    processed_chunks = []

    try:

        for index, chunk in enumerate(chunks):

            embedding = generate_embedding(chunk)

            processed_chunks.append(
                models.DocumentChunk(
                    document_id=document.id,
                    chunk_number=index + 1,
                    content=chunk,
                    embedding=embedding
                )
            )

        # Replace old chunks after successful embedding generation
        db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        db.add_all(processed_chunks)

        db.commit()

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=502,
            detail=(
                "Embedding generation or storage failed. "
                "Check AWS Bedrock access and database."
            )
        ) from error

    return {
        "status": "success",
        "message": "Document chunked and embedded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "total_chunks": len(chunks),
        "embedding_dimensions": 1024
    }


# --------------------------------------------------
# View chunks
# --------------------------------------------------

@app.get("/api/documents/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db)
):

    if db.get(models.Document, document_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    chunks = (
        db.query(models.DocumentChunk)
        .filter(
            models.DocumentChunk.document_id == document_id
        )
        .order_by(models.DocumentChunk.chunk_number)
        .all()
    )

    return [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_number": chunk.chunk_number,
            "content": chunk.content,
            "embedding_dimensions": len(chunk.embedding)
        }
        for chunk in chunks
    ]


# --------------------------------------------------
# Semantic Search using pgvector
# --------------------------------------------------

@app.post("/api/search")
def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):

    query_text = request.query.strip()

    if not query_text:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )

    # Step 1: Generate embedding for the question
    try:
        query_embedding = generate_embedding(query_text)

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate query embedding. Check AWS Bedrock access."
        ) from error

    # Step 2: Calculate cosine distance
    distance = models.DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    # Step 3: Retrieve the top 3 closest chunks
    try:
        results = (
            db.query(
                models.DocumentChunk,
                models.Document.filename,
                distance.label("distance")
            )
            .join(
                models.Document,
                models.Document.id == models.DocumentChunk.document_id
            )
            .order_by(distance.asc())
            .limit(3)
            .all()
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to search document embeddings"
        ) from error

    # Step 4: Format results
    search_results = []

    for chunk, filename, cosine_distance in results:

        distance_value = float(cosine_distance)

        search_results.append({
            "document_id": chunk.document_id,
            "filename": filename,
            "chunk_number": chunk.chunk_number,
            "content": chunk.content,
            "cosine_distance": round(distance_value, 4),
            "cosine_similarity": round(1 - distance_value, 4)
        })

    return {
        "status": "success",
        "query": query_text,
        "total_results": len(search_results),
        "results": search_results
    }

# --------------------------------------------------
# RAG Question Answering
# --------------------------------------------------

@app.post("/api/rag/ask")
def ask_rag_question(
    request: RAGRequest,
    db: Session = Depends(get_db)
):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # Step 1: Security check BEFORE embeddings, database retrieval, or Bedrock.
    security_result = moderation_check(question)

    if not security_result["allowed"]:
        return {
            "status": "blocked",
            "question": question,
            "answer": "Request blocked by security checks.",
            "security": {
                "category": security_result.get("category"),
                "reason": security_result["reason"],
            },
            "total_sources": 0,
            "sources": [],
        }

    # Step 2: Generate question embedding only after input is approved.
    try:
        query_embedding = generate_embedding(question)

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate question embedding"
        ) from error

    # Step 2: Retrieve the top 3 relevant chunks
    distance = models.DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    try:
        results = (
            db.query(
                models.DocumentChunk,
                models.Document.filename,
                distance.label("distance")
            )
            .join(
                models.Document,
                models.Document.id == models.DocumentChunk.document_id
            )
            .order_by(distance.asc())
            .limit(3)
            .all()
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve document context"
        ) from error

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No processed document chunks found. Generate embeddings first."
        )

    # Step 3: Prepare retrieved context
    retrieved_chunks = []

    for chunk, filename, cosine_distance in results:

        retrieved_chunks.append({
            "filename": filename,
            "document_id": chunk.document_id,
            "chunk_number": chunk.chunk_number,
            "content": chunk.content,
            "cosine_distance": round(float(cosine_distance), 4)
        })

    # Step 4: Generate answer using LangChain and Bedrock
    try:
        answer = generate_rag_answer(
            question,
            retrieved_chunks
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate answer using Amazon Bedrock. Check model access and IAM permissions."
        ) from error

    # Step 5: Return answer and source information
    return {
        "status": "success",
        "question": question,
        "answer": answer,
        "total_sources": len(retrieved_chunks),
        "prompt_version": get_prompt_metadata("rag_answer"),
        "sources": [
            {
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "chunk_number": chunk["chunk_number"],
                "cosine_distance": chunk["cosine_distance"]
            }
            for chunk in retrieved_chunks
        ]
    }


# --------------------------------------------------
# Lesson 7: Conversation memory and chat history
# --------------------------------------------------

@app.post("/api/chat/sessions")
def create_chat_session(db: Session = Depends(get_db)):
    """Create a new conversation session."""
    session = models.ChatSession(title="New Conversation")

    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create chat session"
        ) from error

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@app.get("/api/chat/sessions")
def list_chat_sessions(db: Session = Depends(get_db)):
    """Return conversation sessions, newest activity first."""
    sessions = (
        db.query(models.ChatSession)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )

    return [
        {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
        for session in sessions
    ]


@app.get("/api/chat/sessions/{session_id}/messages")
def get_chat_messages(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Return all messages belonging to one conversation."""
    session = db.get(models.ChatSession, session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.id.asc())
        .all()
    )

    return [
        {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at
        }
        for message in messages
    ]


@app.post("/api/chat")
def chat_with_memory(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Answer a question using retrieved document chunks and the
    latest five conversation turns (up to ten messages).
    """
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    session = db.get(models.ChatSession, request.session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found. Create a session first."
        )

    # Fetch the latest 10 messages, then restore chronological order.
    recent_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.id.desc())
        .limit(10)
        .all()
    )
    recent_messages.reverse()

    history = [
        {"role": message.role, "content": message.content}
        for message in recent_messages
    ]

    # Lesson 8: Run retrieval, retrieval evaluation, and answer generation
    # through the compiled LangGraph workflow.
    try:
        graph_result = run_rag_agent(
            question=question,
            history=history,
            db=db
        )
        answer = graph_result["answer"]
        retrieved_chunks = graph_result["retrieved_chunks"]
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "LangGraph RAG workflow failed. Check the backend terminal "
                "for the detailed error and verify Bedrock/database access."
            )
        ) from error

    # Save both messages only after answer generation succeeds.
    try:
        user_message = models.ChatMessage(
            session_id=session.id,
            role="user",
            content=question
        )
        assistant_message = models.ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer
        )

        db.add_all([user_message, assistant_message])

        if session.title == "New Conversation":
            session.title = question[:100]

        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The answer was generated, but the chat messages could not be saved."
        ) from error

    return {
        "status": "success",
        "session_id": session.id,
        "question": question,
        "answer": answer,
        "search_query": graph_result["search_query"],
        "retrieval_status": graph_result["retrieval_status"],
        "total_sources": len(retrieved_chunks),
        "prompt_versions": graph_result["prompt_versions"],
        "sources": [
            {
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "chunk_number": chunk["chunk_number"],
                "cosine_distance": chunk["cosine_distance"]
            }
            for chunk in retrieved_chunks
        ],
        "messages": [
            {
                "id": user_message.id,
                "role": user_message.role,
                "content": user_message.content
            },
            {
                "id": assistant_message.id,
                "role": assistant_message.role,
                "content": assistant_message.content
            }
        ]
    }


# --------------------------------------------------
# Lesson 9: Agentic AI tool calling
# --------------------------------------------------

@app.post("/api/agent/ask")
def ask_agent(request: AgentRequest, db: Session = Depends(get_db)):
    """Run the tool-calling agent with optional conversation history."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    history = []
    session = None
    if request.session_id is not None:
        session = db.get(models.ChatSession, request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")
        previous = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.session_id == session.id)
            .order_by(models.ChatMessage.id.desc())
            .limit(10)
            .all()
        )
        previous.reverse()
        history = [{"role": item.role, "content": item.content} for item in previous]

    try:
        result = run_tool_agent(question=question, history=history, db=db)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Tool-calling agent failed. Check the backend terminal for the detailed error and verify Bedrock tool-use access."
        ) from error

    security = result.get("security", {})
    is_blocked = security.get("status") == "blocked"

    # Do not store blocked prompt-injection attempts in normal chat history.
    if session is not None and not is_blocked:
        try:
            db.add_all([
                models.ChatMessage(session_id=session.id, role="user", content=question),
                models.ChatMessage(session_id=session.id, role="assistant", content=result["answer"]),
            ])
            if session.title == "New Conversation":
                session.title = question[:100]
            db.commit()
        except Exception as error:
            db.rollback()
            raise HTTPException(status_code=500, detail="Agent answered, but chat history could not be saved.") from error

    return {
        "status": "blocked" if is_blocked else "success",
        "question": question,
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "tools_available": ["calculator", "search_knowledge_base"],
        "security": security,
    }