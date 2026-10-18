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
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("A valid HTTP or HTTPS URL is required.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
        raise ValueError("URL must include a valid HTTP or HTTPS scheme and hostname.")

    return value


class WebsiteCreate(BaseModel):
    website_url: str = Field(min_length=1, max_length=1000)
    domain: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("website_url")
    @classmethod
    def validate_website_url(cls, value: str) -> str:
        return validate_http_url(value)


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_url: str
    domain: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class WebsiteListResponse(BaseModel):
    items: list[WebsiteResponse]
    total: int
    limit: int
    offset: int