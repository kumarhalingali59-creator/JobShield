
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportCreate(BaseModel):
    report_type: str = Field(min_length=1, max_length=50)
    target_value: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1)

    @field_validator("report_type", "target_value", "description")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be blank.")
        return value


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_type: str
    target_value: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    limit: int
    offset: int
