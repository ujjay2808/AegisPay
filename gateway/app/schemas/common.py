from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, BaseModel, ConfigDict, Field


def strip_text(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def normalize_currency(value: Any) -> Any:
    return value.strip().upper() if isinstance(value, str) else value


NonBlankText = Annotated[str, BeforeValidator(strip_text)]
CurrencyCode = Annotated[str, BeforeValidator(normalize_currency), Field(pattern=r"^[A-Z]{3}$")]


class Money(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    currency: CurrencyCode


class SpendingConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_amount: Decimal | None = Field(default=None, gt=Decimal("0"), decimal_places=2)
    currency: CurrencyCode | None = None
