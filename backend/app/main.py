
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

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

from app.core.dependencies import get_db
from app.core.request_rate_limit import RequestRateLimitMiddleware

from app.models.company import Company
from app.models.recruiter import Recruiter
from app.models.phone_number import PhoneNumber
from app.models.email import Email
from app.models.website import Website
from app.models.job import Job
from app.models.message import Message


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="JobShield API",
    description="Recruitment Trust Intelligence Platform",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.add_middleware(RequestRateLimitMiddleware)

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
    search_type: str = Field(min_length=1, max_length=30)
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Search query cannot be empty.")

        return value

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, value: str) -> str:
        value = value.strip().lower().replace("-", "_")

        if not value:
            raise ValueError("Search type cannot be empty.")

        return value


# Search fields can contain sensitive information.
# Only explicitly approved fields are returned to clients.
SEARCH_CONFIG = {
    "companies": (
        Company,
        ("name", "legal_name", "website", "description"),
        ("name", "legal_name", "website", "description"),
        "name",
    ),
    "recruiters": (
        Recruiter,
        (
            "name",
            "email",
            "phone",
            "company_name",
            "profile_url",
            "description",
        ),
        ("name", "company_name", "profile_url", "description"),
        "name",
    ),
    "phone_numbers": (
        PhoneNumber,
        ("phone_number", "country_code", "description"),
        ("country_code", "description"),
        "phone_number",
    ),
    "emails": (
        Email,
        ("email_address", "description"),
        ("description",),
        "email_address",
    ),
    "websites": (
        Website,
        ("website_url", "domain", "description"),
        ("website_url", "domain", "description"),
        "website_url",
    ),
    "jobs": (
        Job,
        ("job_url", "title", "company_name", "description"),
        ("job_url", "title", "company_name", "description"),
        "title",
    ),
    "messages": (
        Message,
        ("message_text",),
        (),
        None,
    ),
}

SEARCH_ALIASES = {
    "company": "companies",
    "recruiter": "recruiters",
    "phone": "phone_numbers",
    "email": "emails",
    "website": "websites",
    "job": "jobs",
    "message": "messages",
}

SENSITIVE_SEARCH_TYPES = {
    "emails",
    "phone_numbers",
    "messages",
}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JobShield API",
        "version": "0.1.0",
    }


@app.post("/api/search")
@limiter.limit("30/minute")
def search(
    request: Request,
    search_request: SearchRequest,
    db: Session = Depends(get_db),
):
    search_type = SEARCH_ALIASES.get(
        search_request.search_type,
        search_request.search_type,
    )

    if search_type != "all" and search_type not in SEARCH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Unsupported search_type. Use all, companies, recruiters, "
                "phone_numbers, emails, websites, jobs, or messages."
            ),
        )

    # Escape SQL LIKE wildcard characters so user input is matched literally.
    escaped_query = (
        search_request.query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    pattern = f"%{escaped_query}%"

    types_to_search = (
        list(SEARCH_CONFIG)
        if search_type == "all"
        else [search_type]
    )

    results = []

    # Limit each category to 10 matching records.
    for category in types_to_search:
        model, searchable_fields, output_fields, title_field = (
            SEARCH_CONFIG[category]
        )

        filters = [
            getattr(model, field).ilike(pattern, escape="\\")
            for field in searchable_fields
        ]

        records = (
            db.query(model)
            .filter(or_(*filters))
            .order_by(model.id.desc())
            .limit(10)
            .all()
        )

        for record in records:
            record_data = {
                field: getattr(record, field)
                for field in output_fields
            }

            # Avoid exposing raw email addresses, phone numbers,
            # or message contents through result titles.
            if title_field is None:
                title = (
                    f"{category.replace('_', ' ').title()} #{record.id}"
                )
            else:
                title_value = getattr(record, title_field, None)

                if category == "emails":
                    title = f"Email record #{record.id}"
                elif category == "phone_numbers":
                    title = f"Phone record #{record.id}"
                else:
                    title = title_value or (
                        f"{category.rstrip('s').capitalize()} #{record.id}"
                    )

            results.append(
                {
                    "type": category,
                    "id": record.id,
                    "title": title,
                    "record": record_data,
                }
            )

    # Do not echo sensitive search terms back to the client.
    safe_query = (
        search_request.query
        if search_type not in SENSITIVE_SEARCH_TYPES and search_type != "all"
        else search_type.replace("_", " ").title()
    )

    return {
        "status": "success",
        "search_type": search_type,
        "query": safe_query,
        "total": len(results),
        "results": results,
    }
