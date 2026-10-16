from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecruiterCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    profile_url: str | None = None
    description: str | None = None


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