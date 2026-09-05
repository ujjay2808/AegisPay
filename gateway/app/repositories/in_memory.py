from dataclasses import dataclass

from app.schemas.canonical import CanonicalCart, CanonicalIntent, CanonicalTransaction
from app.schemas.policy import PolicyDecision
from app.schemas.state import CartStatus, IntentStatus, PaymentStatus


@dataclass(frozen=True)
class StoredIntentRecord:
    intent: CanonicalIntent
    status: IntentStatus


@dataclass(frozen=True)
class StoredCartRecord:
    cart: CanonicalCart
    status: CartStatus


@dataclass(frozen=True)
class StoredPaymentRecord:
    transaction: CanonicalTransaction
    status: PaymentStatus
    decision: PolicyDecision


class InMemoryGatewayRepository:
    def __init__(self) -> None:
        self._intents: dict[str, StoredIntentRecord] = {}
        self._carts: dict[str, StoredCartRecord] = {}
        self._payments_by_idempotency: dict[str, StoredPaymentRecord] = {}

    def save_intent(self, intent: CanonicalIntent, status: IntentStatus) -> None:
        self._intents[intent.intent_id] = StoredIntentRecord(intent, status)

    def get_intent(self, intent_id: str) -> StoredIntentRecord | None:
        return self._intents.get(intent_id)

    def save_cart(self, cart: CanonicalCart, status: CartStatus) -> None:
        self._carts[cart.cart_id] = StoredCartRecord(cart, status)

    def get_cart(self, cart_id: str) -> StoredCartRecord | None:
        return self._carts.get(cart_id)

    def update_cart_status(self, cart_id: str, status: CartStatus) -> None:
        record = self._carts[cart_id]
        self._carts[cart_id] = StoredCartRecord(record.cart, status)

    def save_payment(
        self,
        transaction: CanonicalTransaction,
        status: PaymentStatus,
        decision: PolicyDecision,
    ) -> None:
        self._payments_by_idempotency[transaction.idempotency_key] = StoredPaymentRecord(
            transaction,
            status,
            decision,
        )

    def get_payment_by_idempotency_key(self, idempotency_key: str) -> StoredPaymentRecord | None:
        return self._payments_by_idempotency.get(idempotency_key)
