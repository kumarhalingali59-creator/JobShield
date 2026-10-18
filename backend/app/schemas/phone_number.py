from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PhoneNumberCreate(BaseModel):
    phone_number: str = Field(min_length=1, max_length=50)
    country_code: str | None = Field(default=None, max_length=10)
    description: str | None = None

    @field_validator("phone_number")
    @classmethod
    def reject_blank_phone_number(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Phone number must not be blank.")
        return value


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