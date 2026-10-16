from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailCreate(BaseModel):
    email_address: str
    description: str | None = None


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_address: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EmailListResponse(BaseModel):
    items: list[EmailResponse]
    total: int
    limit: int
    offset: int