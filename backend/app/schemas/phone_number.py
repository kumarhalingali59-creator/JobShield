from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PhoneNumberCreate(BaseModel):
    phone_number: str
    country_code: str | None = None
    description: str | None = None


class PhoneNumberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    country_code: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class PhoneNumberListResponse(BaseModel):
    items: list[PhoneNumberResponse]
    total: int
    limit: int
    offset: int