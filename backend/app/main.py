
import hashlib
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File
)

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from pypdf import PdfReader
from docx import Document as DocxDocument

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database import engine, Base, get_db
from app import models
from app.embedding_service import generate_embedding


MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


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

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "characters": len(doc.content),
            "created_at": doc.created_at
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