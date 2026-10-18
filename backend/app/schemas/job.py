from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_http_url(value: str) -> str:
    value = value.strip()

    if not value or any(character.isspace() for character in value):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        # Accessing port also catches malformed port values.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("A valid HTTP or HTTPS URL is required.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
        raise ValueError("URL must include a valid HTTP or HTTPS scheme and hostname.")

    return value


class JobCreate(BaseModel):
    job_url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=500)
    company_name: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str) -> str:
        return validate_http_url(value)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_url: str
    title: str | None
    company_name: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    limit: int
    offset: int