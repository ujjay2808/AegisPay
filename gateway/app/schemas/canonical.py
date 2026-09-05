from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CurrencyCode, NonBlankText, SpendingConstraints
from app.schemas.payment import SimulatedPaymentMethod


class CanonicalIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    agent_id: NonBlankText = Field(min_length=1, max_length=128)
    user_id: NonBlankText = Field(min_length=1, max_length=128)
    purpose: NonBlankText = Field(min_length=1, max_length=500)
    spending_constraints: SpendingConstraints | None = None


class CanonicalLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: NonBlankText = Field(min_length=1, max_length=128)
    name: NonBlankText = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0, le=100_000)
    unit_price: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    line_total: Decimal = Field(ge=Decimal("0"), decimal_places=2)


class CanonicalCart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_id: NonBlankText = Field(min_length=1, max_length=128)
    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_name: NonBlankText = Field(min_length=1, max_length=255)
    items: list[CanonicalLineItem] = Field(min_length=1, max_length=1_000)
    total: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    currency: CurrencyCode


class CanonicalTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: NonBlankText = Field(min_length=1, max_length=128)
    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    cart_id: NonBlankText = Field(min_length=1, max_length=128)
    agent_id: NonBlankText = Field(min_length=1, max_length=128)
    user_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_name: NonBlankText = Field(min_length=1, max_length=255)
    amount: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    currency: CurrencyCode
    payment_method: SimulatedPaymentMethod
    idempotency_key: NonBlankText = Field(min_length=1, max_length=255)
