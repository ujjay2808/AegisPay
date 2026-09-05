from decimal import Decimal

import pytest

from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest, SimulatedPaymentMethod
from app.services.normalization import get_ap2_normalization_service


@pytest.fixture
def normalized_context():
    service = get_ap2_normalization_service()
    intent = service.normalize_intent(
        IntentCreateRequest(
            agent_id="agent-1",
            user_id="user-1",
            purpose="Purchase office supplies",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        ),
        intent_id="intent-1",
    )
    cart = service.normalize_cart(
        CartCreateRequest(
            intent_id="intent-1",
            merchant_id="merchant-1",
            merchant_name="Example Merchant",
            items=[
                {
                    "product_id": "product-1",
                    "name": "Notebook",
                    "quantity": 2,
                    "unit_price": "125.50",
                },
                {
                    "product_id": "product-2",
                    "name": "Pen",
                    "quantity": 3,
                    "unit_price": "10.00",
                },
            ],
            currency="inr",
        ),
        cart_id="cart-1",
        intent=intent,
    )
    return service, intent, cart


def test_ap2_intent_normalizes_to_canonical_model(normalized_context) -> None:
    _, intent, _ = normalized_context

    assert intent.intent_id == "intent-1"
    assert intent.agent_id == "agent-1"
    assert intent.spending_constraints is not None
    assert intent.spending_constraints.currency == "INR"


def test_ap2_cart_calculates_total_and_preserves_relationship(normalized_context) -> None:
    _, intent, cart = normalized_context

    assert cart.intent_id == intent.intent_id
    assert cart.total == Decimal("281.00")
    assert cart.items[0].line_total == Decimal("251.00")
    assert cart.currency == "INR"


def test_ap2_payment_normalizes_protocol_neutral_transaction(normalized_context) -> None:
    service, intent, cart = normalized_context
    transaction = service.normalize_payment(
        PaymentCreateRequest(
            cart_id="cart-1",
            payment_method=SimulatedPaymentMethod.SIMULATED_WALLET,
            idempotency_key="payment-attempt-1",
        ),
        transaction_id="transaction-1",
        intent=intent,
        cart=cart,
    )

    assert transaction.transaction_id == "transaction-1"
    assert transaction.intent_id == "intent-1"
    assert transaction.cart_id == "cart-1"
    assert transaction.amount == Decimal("281.00")
    assert transaction.payment_method == SimulatedPaymentMethod.SIMULATED_WALLET


def test_ap2_adapter_rejects_relationship_mismatch(normalized_context) -> None:
    service, intent, cart = normalized_context

    with pytest.raises(ValueError, match="intent_id"):
        service.normalize_cart(
            CartCreateRequest(
                intent_id="different-intent",
                merchant_id="merchant-1",
                merchant_name="Example Merchant",
                items=[
                    {
                        "product_id": "product-1",
                        "name": "Notebook",
                        "quantity": 1,
                        "unit_price": "10.00",
                    }
                ],
                currency="INR",
            ),
            cart_id="cart-2",
            intent=intent,
        )

    with pytest.raises(ValueError, match="cart_id"):
        service.normalize_payment(
            PaymentCreateRequest(
                cart_id="different-cart",
                payment_method=SimulatedPaymentMethod.SIMULATED_CARD,
                idempotency_key="payment-attempt-2",
            ),
            transaction_id="transaction-2",
            intent=intent,
            cart=cart,
        )
