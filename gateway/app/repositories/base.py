from typing import Protocol

from app.schemas.canonical import CanonicalCart, CanonicalIntent, CanonicalTransaction
from app.schemas.policy import PolicyDecision
from app.schemas.state import CartStatus, IntentStatus, PaymentStatus


class StoredIntent(Protocol):
    intent: CanonicalIntent
    status: IntentStatus


class StoredCart(Protocol):
    cart: CanonicalCart
    status: CartStatus


class StoredPayment(Protocol):
    transaction: CanonicalTransaction
    status: PaymentStatus
    decision: PolicyDecision
    audit_tx_hash: str | None


class GatewayRepository(Protocol):
    def save_intent(self, intent: CanonicalIntent, status: IntentStatus) -> None:
        ...

    def get_intent(self, intent_id: str) -> StoredIntent | None:
        ...

    def save_cart(self, cart: CanonicalCart, status: CartStatus) -> None:
        ...

    def get_cart(self, cart_id: str) -> StoredCart | None:
        ...

    def update_cart_status(self, cart_id: str, status: CartStatus) -> None:
        ...

    def save_payment(
        self,
        transaction: CanonicalTransaction,
        status: PaymentStatus,
        decision: PolicyDecision,
        audit_tx_hash: str | None = None,
    ) -> None:
        ...

    def update_payment_audit_tx_hash(self, payment_id: str, audit_tx_hash: str | None) -> None:
        ...

    def get_payment_by_idempotency_key(self, idempotency_key: str) -> StoredPayment | None:
        ...
