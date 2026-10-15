from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.in_memory import InMemoryGatewayRepository
from app.schemas.cart import CartCreateRequest
from app.schemas.intent import IntentCreateRequest
from app.schemas.payment import PaymentCreateRequest
from app.schemas.state import PaymentStatus
from app.services.mandate_flow import MandateFlowService
from app.services.normalization import get_ap2_normalization_service
from app.services.policy_engine import get_policy_engine


@pytest.fixture(autouse=True)
def clear_dependency_overrides(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "audit_enabled", False, raising=False)
    yield
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "audit_enabled", False, raising=False)


client = TestClient(app)


class FakeAuditClient:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def record_decision(self, transaction, decision):
        self.calls += 1
        return self.value


class RaisesOnUpdateAuditTxHash:
    def __init__(self):
        self.calls = 0

    def record_decision(self, transaction, decision):
        self.calls += 1
        return "0xabc"


def _build_service(audit_client=None) -> MandateFlowService:
    repository = InMemoryGatewayRepository()
    return MandateFlowService(
        repository=repository,
        normalization=get_ap2_normalization_service(),
        policy_engine=get_policy_engine(settings),
        audit_client=audit_client,
    )


def _build_cart_request(
    intent_id: str,
    *,
    merchant_id: str = "merchant-service",
    merchant_name: str = "Service Merchant",
    product_id: str = "product-service",
    product_name: str = "Notebook",
    quantity: int = 2,
    unit_price: str = "125.50",
    currency: str = "INR",
) -> CartCreateRequest:
    return CartCreateRequest(
        intent_id=intent_id,
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        items=[
            {
                "product_id": product_id,
                "name": product_name,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        ],
        currency=currency,
    )


def _build_payment_request(cart_id: str, idempotency_key: str) -> PaymentCreateRequest:
    return PaymentCreateRequest(
        cart_id=cart_id,
        payment_method="SIMULATED_CARD",
        idempotency_key=idempotency_key,
    )


def _create_cart_and_return_service(audit_client=None):
    service = _build_service(audit_client=audit_client)
    intent = service.create_intent(
        IntentCreateRequest(
            agent_id="agent-service",
            user_id="user-service",
            purpose="Purchase office supplies",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        ))[0]
    cart = service.create_cart(_build_cart_request(intent.intent_id))[0]
    return service, cart.cart_id


class FailOnPersistRepository:
    def __init__(self, inner):
        self._inner = inner
        self._session = type("Session", (), {"rollback": lambda self: None})()

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def update_payment_audit_tx_hash(self, payment_id, audit_tx_hash):
        raise RuntimeError("persist failed")


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


def test_payment_persists_audit_hash_when_audit_returns_hex() -> None:
    service, cart_id = _create_cart_and_return_service(audit_client=FakeAuditClient("0xabc"))
    request = _build_payment_request(cart_id, f"audit-hash-{uuid4()}")

    _, _, _, audit_tx_hash = service.create_payment(request)

    assert audit_tx_hash == "0xabc"
    stored_payment = service._repository.get_payment_by_idempotency_key(request.idempotency_key)
    assert stored_payment is not None
    assert stored_payment.audit_tx_hash == "0xabc"


def test_payment_replay_returns_same_hash_and_calls_audit_once() -> None:
    fake_client = FakeAuditClient("0xabc")
    service, cart_id = _create_cart_and_return_service(audit_client=fake_client)
    request = _build_payment_request(cart_id, f"replay-hash-{uuid4()}")

    first = service.create_payment(request)
    second = service.create_payment(request)

    assert first == second
    assert first[3] == "0xabc"
    assert fake_client.calls == 1


def test_payment_saves_when_audit_client_returns_none() -> None:
    service, cart_id = _create_cart_and_return_service(audit_client=FakeAuditClient(None))
    request = _build_payment_request(cart_id, f"audit-none-{uuid4()}")

    _, _, _, audit_tx_hash = service.create_payment(request)

    assert audit_tx_hash is None
    stored_payment = service._repository.get_payment_by_idempotency_key(request.idempotency_key)
    assert stored_payment is not None
    assert stored_payment.audit_tx_hash is None


def test_payment_without_audit_client_has_null_audit_hash() -> None:
    service, cart_id = _create_cart_and_return_service(audit_client=None)
    request = _build_payment_request(cart_id, f"audit-disabled-{uuid4()}")

    _, _, _, audit_tx_hash = service.create_payment(request)

    assert audit_tx_hash is None
    stored_payment = service._repository.get_payment_by_idempotency_key(request.idempotency_key)
    assert stored_payment is not None
    assert stored_payment.audit_tx_hash is None


def test_payment_returns_audit_hash_even_when_persistence_fails() -> None:
    service = _build_service(audit_client=FakeAuditClient("0xabc"))
    intent = service.create_intent(
        IntentCreateRequest(
            agent_id="agent-rollback",
            user_id="user-rollback",
            purpose="Purchase office supplies",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        ))[0]
    cart = service.create_cart(
        _build_cart_request(
            intent.intent_id,
            merchant_id="merchant-rollback",
            merchant_name="Rollback Merchant",
            product_id="product-rollback",
            product_name="Notebook",
            quantity=1,
            unit_price="10.00",
        )
    )[0]
    key = f"audit-persist-fail-{uuid4()}"
    service._repository = FailOnPersistRepository(service._repository)

    _, _, _, audit_tx_hash = service.create_payment(_build_payment_request(cart.cart_id, key))

    assert audit_tx_hash == "0xabc"
    stored_payment = service._repository.get_payment_by_idempotency_key(key)
    assert stored_payment is not None
    assert stored_payment.audit_tx_hash is None


def test_payment_to_blocked_merchant_is_denied_and_logged(monkeypatch) -> None:
    monkeypatch.setattr(settings, "blocked_merchant_ids", "blocked-merchant", raising=False)
    fake_client = FakeAuditClient("0xabc")
    service = _build_service(audit_client=fake_client)
    intent = service.create_intent(
        IntentCreateRequest(
            agent_id="agent-blocked",
            user_id="user-blocked",
            purpose="Purchase office supplies",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        ))[0]
    cart = service.create_cart(
        _build_cart_request(
            intent.intent_id,
            merchant_id="blocked-merchant",
            merchant_name="Blocked Merchant",
            product_id="product-blocked",
            product_name="Notebook",
            quantity=1,
            unit_price="10.00",
        )
    )[0]
    request = _build_payment_request(cart.cart_id, f"blocked-{uuid4()}")

    transaction, status, decision, audit_tx_hash = service.create_payment(request)

    assert status == PaymentStatus.DENIED
    assert decision.decision.value == "DENIED"
    assert decision.reason_code == "MERCHANT_BLOCKED"
    assert audit_tx_hash == "0xabc"
    assert fake_client.calls == 1
    stored_payment = service._repository.get_payment_by_idempotency_key(request.idempotency_key)
    assert stored_payment is not None
    assert stored_payment.status == PaymentStatus.DENIED
    assert stored_payment.decision.reason_code == "MERCHANT_BLOCKED"
    assert transaction.merchant_id == "blocked-merchant"


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
