from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebsiteCreate(BaseModel):
    website_url: str
    domain: str | None = None
    description: str | None = None


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