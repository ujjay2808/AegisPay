from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import NonBlankText
from app.schemas.policy import PolicyDecisionType


class SimulatedPaymentMethod(StrEnum):
    SIMULATED_CARD = "SIMULATED_CARD"
    SIMULATED_BANK = "SIMULATED_BANK"
    SIMULATED_WALLET = "SIMULATED_WALLET"


class PaymentDecision(StrEnum):
    APPROVED = "APPROVED"
    ESCALATED = "ESCALATED"
    DENIED = "DENIED"


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_id: NonBlankText = Field(min_length=1, max_length=128)
    payment_method: SimulatedPaymentMethod
    idempotency_key: NonBlankText = Field(min_length=1, max_length=255)


class PaymentCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: NonBlankText = Field(min_length=1, max_length=128)
    cart_id: NonBlankText = Field(min_length=1, max_length=128)
    decision: PolicyDecisionType
    status: str = Field(min_length=1, max_length=32)
    reason_code: NonBlankText = Field(max_length=64)
    reason: NonBlankText = Field(max_length=500)
