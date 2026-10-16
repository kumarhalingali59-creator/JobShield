
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceCreate(BaseModel):
    report_id: int = Field(gt=0)
    file_name: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=1000)
    content_type: str = Field(min_length=1, max_length=100)
    file_size: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("file_name", "storage_path", "content_type")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    file_name: str
    storage_path: str
    content_type: str
    file_size: int
    description: str | None
    created_at: datetime


class EvidenceListResponse(BaseModel):
    items: list[EvidenceResponse]
    total: int
    limit: int
    offset: int
