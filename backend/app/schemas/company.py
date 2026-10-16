from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    legal_name: str | None = None
    description: str | None = None
    website: str | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str | None
    description: str | None
    website: str | None
    created_at: datetime
    updated_at: datetime

class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    limit: int
    offset: int