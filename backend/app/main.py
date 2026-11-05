
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from pypdf import PdfReader
from docx import Document as DocxDocument

from app.database import engine, Base, get_db
from app import models


MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="VPRO Agent Platform",
    description="Agentic AI Chatbot Backend",
    version="1.0.0",
    lifespan=lifespan
)

#Allow React frontend to communicate with backend
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


# Extract text from uploaded documents
def extract_text(filename, file_content):

    filename = filename.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(BytesIO(file_content))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif filename.endswith(".docx"):
        document = DocxDocument(BytesIO(file_content))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    elif filename.endswith(".txt"):
        return file_content.decode("utf-8-sig")

    raise ValueError("Unsupported file format")


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
            detail="pgvector extension is not enabled"
        )

    return {
        "status": "success",
        "message": "pgvector is enabled",
        "version": result
    }


# Document table health API
@app.get("/api/documents/table-health")
def document_table_health(db: Session = Depends(get_db)):

    db.execute(text("SELECT * FROM documents LIMIT 0"))

    return {
        "status": "success",
        "message": "Documents table is ready"
    }


# Upload document API
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

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
            detail="Uploaded file is empty"
        )

    try:
        extracted_text = extract_text(filename, content)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Unable to read document. Check the file format."
        ) from error

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No readable text found in document"
        )

    document = models.Document(
        filename=filename,
        content=extracted_text
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save document"
        )

    return {
        "status": "success",
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "characters_extracted": len(extracted_text)
    }


# Retrieve uploaded documents
@app.get("/api/documents")
def get_documents(db: Session = Depends(get_db)):

    documents = (
        db.query(models.Document)
        .order_by(models.Document.id.desc())
        .all()
    )

    return [
        {
            "id": document.id,
            "filename": document.filename,
            "characters": len(document.content),
            "created_at": document.created_at
        }
        for document in documents
    ]