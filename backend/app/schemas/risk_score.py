
from pydantic import BaseModel, Field


class RiskAssessmentRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=50)
    target_value: str = Field(min_length=1, max_length=1000)
    signal_types: list[str] = Field(default_factory=list, max_length=20)
    has_sufficient_evidence: bool = False


class RiskSignalResponse(BaseModel):
    signal_type: str
    severity: str
    points: int
    description: str
    source: str


class RiskAssessmentResponse(BaseModel):
    id: int
    target_type: str
    target_value: str
    score: int | None
    risk_level: str
    explanation: str
    signals: list[RiskSignalResponse]
