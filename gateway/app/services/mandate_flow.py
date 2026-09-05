from dataclasses import dataclass
from uuid import uuid4

from app.repositories.base import GatewayRepository
from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest
from app.schemas.policy import PolicyDecision
from app.schemas.state import CartStatus, IntentStatus, PaymentStatus
from app.services.normalization import NormalizationService
from app.services.policy_engine import PolicyEngine


@dataclass
class FlowError(Exception):
    code: str
    message: str
    status_code: int


class MandateFlowService:
    def __init__(
        self,
        repository: GatewayRepository,
        normalization: NormalizationService,
        policy_engine: PolicyEngine,
    ) -> None:
        self._repository = repository
        self._normalization = normalization
        self._policy_engine = policy_engine

    def create_intent(self, request: IntentCreateRequest):
        intent = self._normalization.normalize_intent(request, intent_id=str(uuid4()))
        self._repository.save_intent(intent, IntentStatus.ACTIVE)
        return intent, IntentStatus.ACTIVE

    def create_cart(self, request: CartCreateRequest):
        stored_intent = self._repository.get_intent(request.intent_id)
        if stored_intent is None:
            raise FlowError("INTENT_NOT_FOUND", "Intent was not found", 404)
        if stored_intent.status != IntentStatus.ACTIVE:
            raise FlowError("INVALID_INTENT_STATE", "Intent is not active", 409)

        try:
            cart = self._normalization.normalize_cart(
                request,
                cart_id=str(uuid4()),
                intent=stored_intent.intent,
            )
        except ValueError as error:
            raise FlowError("INVALID_CART", str(error), 422) from error

        self._repository.save_cart(cart, CartStatus.READY_FOR_PAYMENT)
        return cart, CartStatus.READY_FOR_PAYMENT

    def create_payment(self, request: PaymentCreateRequest):
        existing_payment = self._repository.get_payment_by_idempotency_key(request.idempotency_key)
        if existing_payment is not None:
            if existing_payment.transaction.cart_id != request.cart_id:
                raise FlowError(
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "Idempotency key is already associated with another cart",
                    409,
                )
            return existing_payment.transaction, existing_payment.status, existing_payment.decision

        stored_cart = self._repository.get_cart(request.cart_id)
        if stored_cart is None:
            raise FlowError("CART_NOT_FOUND", "Cart was not found", 404)
        if stored_cart.status != CartStatus.READY_FOR_PAYMENT:
            raise FlowError("INVALID_CART_STATE", "Cart is not payable", 409)

        stored_intent = self._repository.get_intent(stored_cart.cart.intent_id)
        if stored_intent is None:
            raise FlowError("INTENT_NOT_FOUND", "Cart intent was not found", 404)

        try:
            transaction = self._normalization.normalize_payment(
                request,
                transaction_id=str(uuid4()),
                intent=stored_intent.intent,
                cart=stored_cart.cart,
            )
        except ValueError as error:
            raise FlowError("INVALID_PAYMENT", str(error), 422) from error

        decision = self._policy_engine.evaluate(transaction, stored_intent.intent)
        payment_status = PaymentStatus(decision.decision.value)
        self._repository.save_payment(transaction, payment_status, decision)
        self._repository.update_cart_status(request.cart_id, CartStatus.PAYMENT_PENDING)
        return transaction, payment_status, decision
