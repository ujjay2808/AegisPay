from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aegispay-gateway"}


def test_versioned_routes_are_registered() -> None:
    paths = set(app.openapi()["paths"])

    assert "/api/v1/mandates/intent" in paths
    assert "/api/v1/mandates/cart" in paths
    assert "/api/v1/mandates/payment" in paths


def test_cart_response_has_typed_contract() -> None:
    intent = client.post(
        "/api/v1/mandates/intent",
        json={"agent_id": "contract-agent", "user_id": "contract-user", "purpose": "Contract test"},
    )
    cart = client.post(
        "/api/v1/mandates/cart",
        json={
            "intent_id": intent.json()["intent_id"],
            "merchant_id": "contract-merchant",
            "merchant_name": "Contract Merchant",
            "items": [{"product_id": "contract-product", "name": "Item", "quantity": 1, "unit_price": "10.00"}],
            "currency": "INR",
        },
    )

    assert cart.status_code == 201
    assert set(cart.json()) == {"cart_id", "intent_id", "total", "status"}
    assert cart.json()["total"] == {"amount": "10.00", "currency": "INR"}
