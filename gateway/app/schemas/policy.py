from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PolicyDecisionType(StrEnum):
    APPROVED = "APPROVED"
    ESCALATED = "ESCALATED"
    DENIED = "DENIED"


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecisionType
    reason_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=500)
