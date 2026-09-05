from decimal import Decimal

from app.schemas.canonical import (
    CanonicalCart,
    CanonicalIntent,
    CanonicalLineItem,
    CanonicalTransaction,
)
from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest


class AP2Adapter:
    def normalize_intent(self, request: IntentCreateRequest, *, intent_id: str) -> CanonicalIntent:
        return CanonicalIntent(
            intent_id=intent_id,
            agent_id=request.agent_id,
            user_id=request.user_id,
            purpose=request.purpose,
            spending_constraints=request.spending_constraints,
        )

    def normalize_cart(
        self,
        request: CartCreateRequest,
        *,
        cart_id: str,
        intent: CanonicalIntent,
    ) -> CanonicalCart:
        if request.intent_id != intent.intent_id:
            raise ValueError("Cart intent_id does not match the canonical intent")

        if (
            intent.spending_constraints is not None
            and intent.spending_constraints.currency is not None
            and intent.spending_constraints.currency != request.currency
        ):
            raise ValueError("Cart currency does not match the intent currency constraint")

        items = [
            CanonicalLineItem(
                product_id=item.product_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.unit_price * item.quantity,
            )
            for item in request.items
        ]
        total = sum((item.line_total for item in items), Decimal("0"))

        return CanonicalCart(
            cart_id=cart_id,
            intent_id=intent.intent_id,
            merchant_id=request.merchant_id,
            merchant_name=request.merchant_name,
            items=items,
            total=total,
            currency=request.currency,
        )

    def normalize_payment(
        self,
        request: PaymentCreateRequest,
        *,
        transaction_id: str,
        intent: CanonicalIntent,
        cart: CanonicalCart,
    ) -> CanonicalTransaction:
        if request.cart_id != cart.cart_id:
            raise ValueError("Payment cart_id does not match the canonical cart")
        if cart.intent_id != intent.intent_id:
            raise ValueError("Canonical cart does not belong to the canonical intent")

        return CanonicalTransaction(
            transaction_id=transaction_id,
            intent_id=intent.intent_id,
            cart_id=cart.cart_id,
            agent_id=intent.agent_id,
            user_id=intent.user_id,
            merchant_id=cart.merchant_id,
            merchant_name=cart.merchant_name,
            amount=cart.total,
            currency=cart.currency,
            payment_method=request.payment_method,
            idempotency_key=request.idempotency_key,
        )
