from app.protocols.ap2 import AP2Adapter
from app.protocols.base import ProtocolAdapter
from app.schemas.canonical import CanonicalCart, CanonicalIntent, CanonicalTransaction
from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest


class NormalizationService:
    def __init__(self, adapter: ProtocolAdapter) -> None:
        self._adapter = adapter

    def normalize_intent(self, request: IntentCreateRequest, *, intent_id: str) -> CanonicalIntent:
        return self._adapter.normalize_intent(request, intent_id=intent_id)

    def normalize_cart(
        self,
        request: CartCreateRequest,
        *,
        cart_id: str,
        intent: CanonicalIntent,
    ) -> CanonicalCart:
        return self._adapter.normalize_cart(request, cart_id=cart_id, intent=intent)

    def normalize_payment(
        self,
        request: PaymentCreateRequest,
        *,
        transaction_id: str,
        intent: CanonicalIntent,
        cart: CanonicalCart,
    ) -> CanonicalTransaction:
        return self._adapter.normalize_payment(
            request,
            transaction_id=transaction_id,
            intent=intent,
            cart=cart,
        )


def get_ap2_normalization_service() -> NormalizationService:
    return NormalizationService(AP2Adapter())
