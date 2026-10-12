from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings


app = FastAPI(
    title="JobShield API",
    description="Recruitment Trust Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    search_type: str
    query: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JobShield API",
        "config_loaded": True,
    }


@app.post("/api/search")
def search(request: SearchRequest):
    return {
        "status": "received",
        "search_type": request.search_type,
        "query": request.query,
        "message": "Search request received successfully.",
    }