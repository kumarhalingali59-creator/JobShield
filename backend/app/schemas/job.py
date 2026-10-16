from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    job_url: str
    title: str | None = None
    company_name: str | None = None
    description: str | None = None


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