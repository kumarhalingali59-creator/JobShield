from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.companies import router as companies_router
from app.api.recruiters import router as recruiters_router
from app.api.phone_numbers import router as phone_numbers_router
from app.api.emails import router as emails_router
from app.api.websites import router as websites_router
from app.api.jobs import router as jobs_router
from app.api.messages import router as messages_router
from app.api.reports import router as reports_router
from app.api.evidence import router as evidence_router
from app.api.risk_scores import router as risk_scores_router
from app.api.auth import router as auth_router
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


app.include_router(companies_router)
app.include_router(recruiters_router)
app.include_router(phone_numbers_router)
app.include_router(emails_router)
app.include_router(websites_router)
app.include_router(jobs_router)
app.include_router(messages_router)
app.include_router(reports_router)
app.include_router(evidence_router)
app.include_router(risk_scores_router)
app.include_router(auth_router)


class SearchRequest(BaseModel):
    search_type: str
    query: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JobShield API",
        "version": "0.1.0",
    }


@app.post("/api/search")
def search(request: SearchRequest):
    return {
        "status": "received",
        "search_type": request.search_type,
        "query": request.query,
        "message": "Search request received successfully.",
    }