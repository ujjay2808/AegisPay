from typing import Protocol

from app.schemas.canonical import (
    CanonicalCart,
    CanonicalIntent,
    CanonicalTransaction,
)
from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest


class ProtocolAdapter(Protocol):
    def normalize_intent(self, request: IntentCreateRequest, *, intent_id: str) -> CanonicalIntent:
        ...

    def normalize_cart(
        self,
        request: CartCreateRequest,
        *,
        cart_id: str,
        intent: CanonicalIntent,
    ) -> CanonicalCart:
        ...

    def normalize_payment(
        self,
        request: PaymentCreateRequest,
        *,
        transaction_id: str,
        intent: CanonicalIntent,
        cart: CanonicalCart,
    ) -> CanonicalTransaction:
        ...
