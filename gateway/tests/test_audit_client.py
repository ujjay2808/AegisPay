import re
import json
from decimal import Decimal

import httpx

from app.schemas.canonical import CanonicalTransaction
from app.schemas.policy import PolicyDecision, PolicyDecisionType
from app.services.audit_client import AuditClient


def _sample_transaction() -> CanonicalTransaction:
    return CanonicalTransaction(
        transaction_id="txn-123",
        intent_id="intent-123",
        cart_id="cart-123",
        agent_id="agent-123",
        user_id="user-123",
        merchant_id="merchant-123",
        merchant_name="Merchant",
        amount=Decimal("251.00"),
        currency="INR",
        payment_method="SIMULATED_CARD",
        idempotency_key="idem-123",
    )


def _sample_decision() -> PolicyDecision:
    return PolicyDecision(
        decision=PolicyDecisionType.APPROVED,
        reason_code="WITHIN_SPEND_LIMIT",
        reason="Transaction is within the configured spending limit",
    )


def test_record_decision_hash_is_deterministic_and_has_hex_shape() -> None:
    seen_hashes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        match = re.search(r'"decisionHash":"([^"]+)"', body)
        assert match is not None
        seen_hashes.append(match.group(1))
        return httpx.Response(200, json={"txHash": "0xabc"})

    client = AuditClient(
        audit_service_url="http://localhost:8080",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    tx = _sample_transaction()
    decision = _sample_decision()

    result_one = client.record_decision(tx, decision)
    result_two = client.record_decision(tx, decision)

    assert result_one == "0xabc"
    assert result_two == "0xabc"
    assert len(seen_hashes) == 2
    assert seen_hashes[0] == seen_hashes[1]
    assert re.fullmatch(r"0x[a-f0-9]{64}", seen_hashes[0]) is not None


def test_record_decision_sends_expected_payload_shape() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["json"] = json.loads(request.read().decode("utf-8"))
        return httpx.Response(200, json={"txHash": "0xdef"})

    client = AuditClient(
        audit_service_url="http://localhost:8080",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    tx_hash = client.record_decision(_sample_transaction(), _sample_decision())

    assert tx_hash == "0xdef"
    assert captured["method"] == "POST"
    assert captured["url"] == "http://localhost:8080/api/decisions"
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"decisionHash", "decision"}
    assert payload["decision"] == "APPROVED"
    assert re.fullmatch(r"0x[a-f0-9]{64}", str(payload["decisionHash"])) is not None


def test_record_decision_failure_or_timeout_returns_none() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    timeout_client = AuditClient(
        audit_service_url="http://localhost:8080",
        timeout_seconds=0.001,
        transport=httpx.MockTransport(timeout_handler),
    )

    assert timeout_client.record_decision(_sample_transaction(), _sample_decision()) is None

    def failure_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    failure_client = AuditClient(
        audit_service_url="http://localhost:8080",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(failure_handler),
    )

    assert failure_client.record_decision(_sample_transaction(), _sample_decision()) is None


def test_record_decision_invalid_url_returns_none() -> None:
    client = AuditClient(
        audit_service_url="not a url",
        timeout_seconds=1.0,
    )

    assert client.record_decision(_sample_transaction(), _sample_decision()) is None
