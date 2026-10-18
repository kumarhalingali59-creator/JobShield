from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_http_url(value: str) -> str:
    value = value.strip()

    if not value or any(character.isspace() for character in value):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("A valid HTTP or HTTPS URL is required.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
        raise ValueError("URL must include a valid HTTP or HTTPS scheme and hostname.")

    return value


class RecruiterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company_name: str | None = Field(default=None, max_length=255)
    profile_url: str | None = Field(default=None, max_length=500)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recruiter name must not be blank.")
        return value

    @field_validator("profile_url")
    @classmethod
    def validate_profile_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_http_url(value)


class RecruiterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone: str | None
    company_name: str | None
    profile_url: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class RecruiterListResponse(BaseModel):
    items: list[RecruiterResponse]
    total: int
    limit: int
    offset: int


class PublicRecruiterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_name: str | None
    profile_url: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class PublicRecruiterListResponse(BaseModel):
    items: list[PublicRecruiterResponse]
    total: int
    limit: int
    offset: int
