
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


#Create FastAPI application
app = FastAPI(
    title="VPRO Agent Platform",
    description="Agentic AI Chatbot Backend",
    version="1.0.0"
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

# Home API
@app.get("/")
def home():
    return {
        "message": "Welcome to VPRO Agent Platform",
        "status": "Backend Running"
    }

#Health Check API
@app.get("/api/health")
def health_check():
    return {
        "status": "success",
        "message": "FASTAPI Backend is connected successfully"

    }