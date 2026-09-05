from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


client = TestClient(app)


def test_malformed_request_uses_consistent_error_shape() -> None:
    response = client.post("/api/v1/mandates/intent", json={"agent_id": "agent-only"})

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed",
    }


def test_missing_cart_uses_consistent_error_shape() -> None:
    response = client.post(
        "/api/v1/mandates/payment",
        json={
            "cart_id": "missing-cart",
            "payment_method": "SIMULATED_CARD",
            "idempotency_key": "missing-cart-key",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"code": "CART_NOT_FOUND", "message": "Cart was not found"}


def test_idempotency_key_conflict_is_explicit() -> None:
    idempotency_key = f"shared-error-key-{uuid4()}"
    first_intent = client.post(
        "/api/v1/mandates/intent",
        json={"agent_id": "error-agent-1", "user_id": "error-user-1", "purpose": "First"},
    )
    second_intent = client.post(
        "/api/v1/mandates/intent",
        json={"agent_id": "error-agent-2", "user_id": "error-user-2", "purpose": "Second"},
    )
    carts = []
    for intent in (first_intent, second_intent):
        response = client.post(
            "/api/v1/mandates/cart",
            json={
                "intent_id": intent.json()["intent_id"],
                "merchant_id": "error-merchant",
                "merchant_name": "Error Merchant",
                "items": [{"product_id": "error-product", "name": "Item", "quantity": 1, "unit_price": "10.00"}],
                "currency": "INR",
            },
        )
        carts.append(response.json()["cart_id"])

    first_payment = client.post(
        "/api/v1/mandates/payment",
        json={"cart_id": carts[0], "payment_method": "SIMULATED_CARD", "idempotency_key": idempotency_key},
    )
    conflict = client.post(
        "/api/v1/mandates/payment",
        json={"cart_id": carts[1], "payment_method": "SIMULATED_CARD", "idempotency_key": idempotency_key},
    )

    assert first_payment.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json() == {
        "code": "IDEMPOTENCY_KEY_CONFLICT",
        "message": "Idempotency key is already associated with another cart",
    }
