from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.cart import CartCreateRequest
from app.schemas.common import Money, SpendingConstraints
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest, SimulatedPaymentMethod


def test_intent_request_accepts_valid_data() -> None:
    request = IntentCreateRequest(
        agent_id="agent-1",
        user_id="user-1",
        purpose="Purchase office supplies",
        spending_constraints={"max_amount": "5000.00", "currency": "inr"},
    )

    assert request.spending_constraints is not None
    assert request.spending_constraints.max_amount == Decimal("5000.00")
    assert request.spending_constraints.currency == "INR"


def test_intent_request_rejects_blank_required_values() -> None:
    with pytest.raises(ValidationError):
        IntentCreateRequest(agent_id="", user_id="user-1", purpose="Purchase")

    with pytest.raises(ValidationError):
        IntentCreateRequest(agent_id="agent-1", user_id="user-1", purpose=" ")


def test_spending_constraints_require_positive_limit() -> None:
    with pytest.raises(ValidationError):
        SpendingConstraints(max_amount=0, currency="INR")


def test_cart_request_validates_items_and_currency() -> None:
    request = CartCreateRequest(
        intent_id="intent-1",
        merchant_id="merchant-1",
        merchant_name="Example Merchant",
        items=[
            {
                "product_id": "product-1",
                "name": "Notebook",
                "quantity": 2,
                "unit_price": "125.50",
            }
        ],
        currency="inr",
    )

    assert request.currency == "INR"
    assert request.items[0].unit_price == Decimal("125.50")

    with pytest.raises(ValidationError):
        CartCreateRequest(
            intent_id="intent-1",
            merchant_id="merchant-1",
            merchant_name="Example Merchant",
            items=[],
            currency="INR",
        )

    with pytest.raises(ValidationError):
        CartCreateRequest(
            intent_id="intent-1",
            merchant_id="merchant-1",
            merchant_name="Example Merchant",
            items=[
                {
                    "product_id": "product-1",
                    "name": "Notebook",
                    "quantity": 1,
                    "unit_price": "-1.00",
                }
            ],
            currency="INR",
        )


def test_payment_request_only_accepts_simulated_methods() -> None:
    request = PaymentCreateRequest(
        cart_id="cart-1",
        payment_method=SimulatedPaymentMethod.SIMULATED_CARD,
        idempotency_key="payment-attempt-1",
    )

    assert request.payment_method == SimulatedPaymentMethod.SIMULATED_CARD

    with pytest.raises(ValidationError):
        PaymentCreateRequest(
            cart_id="cart-1",
            payment_method="REAL_CARD",
            idempotency_key="payment-attempt-1",
        )


def test_money_rejects_malformed_currency() -> None:
    with pytest.raises(ValidationError):
        Money(amount="10.00", currency="rupees")
