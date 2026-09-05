from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


client = TestClient(app)


def create_intent() -> str:
    response = client.post(
        "/api/v1/mandates/intent",
        json={
            "agent_id": "agent-flow",
            "user_id": "user-flow",
            "purpose": "Purchase office supplies",
            "spending_constraints": {"max_amount": "5000", "currency": "INR"},
        },
    )
    assert response.status_code == 201
    return response.json()["intent_id"]


def create_cart() -> str:
    intent_id = create_intent()
    response = client.post(
        "/api/v1/mandates/cart",
        json={
            "intent_id": intent_id,
            "merchant_id": "merchant-flow",
            "merchant_name": "Flow Merchant",
            "items": [
                {
                    "product_id": "product-flow",
                    "name": "Notebook",
                    "quantity": 2,
                    "unit_price": "125.50",
                }
            ],
            "currency": "INR",
        },
    )
    assert response.status_code == 201
    assert response.json()["total"] == {"amount": "251.00", "currency": "INR"}
    return response.json()["cart_id"]


def test_intent_creation_returns_identifier_and_active_state() -> None:
    response = client.post(
        "/api/v1/mandates/intent",
        json={
            "agent_id": "agent-1",
            "user_id": "user-1",
            "purpose": "Purchase a book",
        },
    )

    assert response.status_code == 201
    assert response.json()["intent_id"]
    assert response.json()["status"] == "ACTIVE"


def test_cart_rejects_unknown_intent() -> None:
    response = client.post(
        "/api/v1/mandates/cart",
        json={
            "intent_id": "missing-intent",
            "merchant_id": "merchant-1",
            "merchant_name": "Merchant",
            "items": [
                {
                    "product_id": "product-1",
                    "name": "Book",
                    "quantity": 1,
                    "unit_price": "10.00",
                }
            ],
            "currency": "INR",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"code": "INTENT_NOT_FOUND", "message": "Intent was not found"}


def test_payment_flow_and_idempotency() -> None:
    cart_id = create_cart()
    payload = {
        "cart_id": cart_id,
        "payment_method": "SIMULATED_CARD",
        "idempotency_key": f"flow-payment-1-{uuid4()}",
    }

    first_response = client.post("/api/v1/mandates/payment", json=payload)
    second_response = client.post("/api/v1/mandates/payment", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json() == second_response.json()
    assert first_response.json()["decision"] == "APPROVED"
    assert first_response.json()["status"] == "APPROVED"
    assert first_response.json()["reason_code"] == "WITHIN_SPEND_LIMIT"


def test_payment_rejects_second_operation_for_same_cart() -> None:
    cart_id = create_cart()
    first_response = client.post(
        "/api/v1/mandates/payment",
        json={
            "cart_id": cart_id,
            "payment_method": "SIMULATED_BANK",
            "idempotency_key": f"flow-payment-2-{uuid4()}",
        },
    )
    second_response = client.post(
        "/api/v1/mandates/payment",
        json={
            "cart_id": cart_id,
            "payment_method": "SIMULATED_BANK",
            "idempotency_key": f"flow-payment-3-{uuid4()}",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["code"] == "INVALID_CART_STATE"


def test_payment_over_spend_cap_is_escalated() -> None:
    intent_id = create_intent()
    response = client.post(
        "/api/v1/mandates/cart",
        json={
            "intent_id": intent_id,
            "merchant_id": "merchant-large",
            "merchant_name": "Large Merchant",
            "items": [
                {
                    "product_id": "product-large",
                    "name": "Expensive item",
                    "quantity": 1,
                    "unit_price": "5000.01",
                }
            ],
            "currency": "INR",
        },
    )
    cart_id = response.json()["cart_id"]

    payment = client.post(
        "/api/v1/mandates/payment",
        json={
            "cart_id": cart_id,
            "payment_method": "SIMULATED_CARD",
            "idempotency_key": f"flow-payment-over-cap-{uuid4()}",
        },
    )

    assert payment.status_code == 201
    assert payment.json()["decision"] == "ESCALATED"
    assert payment.json()["status"] == "ESCALATED"
    assert payment.json()["reason_code"] == "SPEND_LIMIT_EXCEEDED"
