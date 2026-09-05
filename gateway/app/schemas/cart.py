from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CurrencyCode, Money, NonBlankText


class CartItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: NonBlankText = Field(min_length=1, max_length=128)
    name: NonBlankText = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0, le=100_000)
    unit_price: Decimal = Field(ge=Decimal("0"), decimal_places=2)


class CartCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_id: NonBlankText = Field(min_length=1, max_length=128)
    merchant_name: NonBlankText = Field(min_length=1, max_length=255)
    items: list[CartItemCreate] = Field(min_length=1, max_length=1_000)
    currency: CurrencyCode

class CartCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_id: NonBlankText = Field(min_length=1, max_length=128)
    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    total: Money
    status: str = Field(min_length=1, max_length=32)
