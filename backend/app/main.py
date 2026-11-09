
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.orm import Session

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database import engine, Base, get_db
from app import models
from app.embedding_service import generate_embedding


# Create database extension and tables
@asynccontextmanager
async def lifespan(app: FastAPI):

    with engine.begin() as connection:
        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )

    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title="VPRO Agent Platform",
    description="Agentic AI Chatbot Backend",
    version="1.0.0",
    lifespan=lifespan
)


# React frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Home API
@app.get("/")
def home():

    return {
        "message": "Welcome to VPRO Agent Platform",
        "status": "Backend Running"
    }


# Database health API
@app.get("/api/db-health")
def database_health(db: Session = Depends(get_db)):

    db.execute(text("SELECT 1"))

    return {
        "status": "success",
        "message": "PostgreSQL connected successfully"
    }


# pgvector health API
@app.get("/api/vector-health")
def vector_health(db: Session = Depends(get_db)):

    result = db.execute(
        text(
            "SELECT extversion FROM pg_extension "
            "WHERE extname = 'vector'"
        )
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


# Upload document listing API
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


# Process document into chunks and embeddings
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

    # Split document into smaller chunks
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

    # Generate embeddings
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

        # Replace previously generated chunks
        db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        db.add_all(processed_chunks)
        db.commit()

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=502,
            detail="Embedding generation or database storage failed"
        ) from error

    return {
        "status": "success",
        "message": "Document chunked and embedded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "total_chunks": len(chunks),
        "embedding_dimensions": 1024
    }


# Retrieve document chunks
@app.get("/api/documents/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db)
):

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