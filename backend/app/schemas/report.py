from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    report_type: str = Field(min_length=1, max_length=50)
    target_value: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1)


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