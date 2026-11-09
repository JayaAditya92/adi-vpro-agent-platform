
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app import models


# Create database tables when application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


# Create FastAPI application
app = FastAPI(
    title="VPRO Agent Platform",
    description="Agentic AI Chatbot Backend",
    version="1.0.0",
    lifespan=lifespan
)


# Allow React frontend to communicate
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


# Database connection API
@app.get("/api/db-health")
def database_health(db: Session = Depends(get_db)):

    db.execute(text("SELECT 1"))

    return {
        "status": "success",
        "message": "PostgreSQL connected successfully"
    }


# pgvector verification API
@app.get("/api/vector-health")
def vector_health(db: Session = Depends(get_db)):

    result = db.execute(
        text(
            "SELECT extversion FROM pg_extension "
            "WHERE extname = 'vector'"
        )
    ).scalar_one_or_none()

    if result is None:
        return {
            "status": "error",
            "message": "pgvector extension is not enabled"
        }

    return {
        "status": "success",
        "message": "pgvector is enabled",
        "version": result
    }


# Document table verification API
@app.get("/api/documents/table-health")
def document_table_health(db: Session = Depends(get_db)):

    db.execute(text("SELECT * FROM documents LIMIT 0"))

    return {
        "status": "success",
        "message": "Documents table is ready"
    }