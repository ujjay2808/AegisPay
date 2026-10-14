from decimal import Decimal

from app.core.config import parse_blocked_merchant_ids
from app.schemas.canonical import CanonicalIntent, CanonicalTransaction
from app.schemas.payment import SimulatedPaymentMethod
from app.schemas.policy import PolicyDecisionType
from app.services.policy_engine import (
    BlocklistThenSpendCapPolicy,
    MerchantBlocklistPolicy,
    PolicyEngine,
    SpendCapPolicy,
)


def make_intent(max_amount: str | None = None, currency: str | None = None) -> CanonicalIntent:
    constraints = None
    if max_amount is not None:
        constraints = {"max_amount": max_amount, "currency": currency}
    return CanonicalIntent(
        intent_id="intent-1",
        agent_id="agent-1",
        user_id="user-1",
        purpose="Purchase supplies",
        spending_constraints=constraints,
    )


def make_transaction(amount: str, currency: str = "INR", merchant_id: str = "merchant-1") -> CanonicalTransaction:
    return CanonicalTransaction(
        transaction_id="transaction-1",
        intent_id="intent-1",
        cart_id="cart-1",
        agent_id="agent-1",
        user_id="user-1",
        merchant_id=merchant_id,
        merchant_name="Merchant",
        amount=amount,
        currency=currency,
        payment_method=SimulatedPaymentMethod.SIMULATED_CARD,
        idempotency_key="payment-1",
    )


def make_engine() -> PolicyEngine:
    return PolicyEngine(SpendCapPolicy(maximum_amount=Decimal("5000.00"), currency="INR"))


def test_amount_within_cap_is_approved() -> None:
    decision = make_engine().evaluate(make_transaction("4999.99"), make_intent())

    assert decision.decision == PolicyDecisionType.APPROVED
    assert decision.reason_code == "WITHIN_SPEND_LIMIT"


def test_amount_at_cap_is_approved() -> None:
    decision = make_engine().evaluate(make_transaction("5000.00"), make_intent())

    assert decision.decision == PolicyDecisionType.APPROVED


def test_amount_over_cap_is_escalated() -> None:
    decision = make_engine().evaluate(make_transaction("5000.01"), make_intent())

    assert decision.decision == PolicyDecisionType.ESCALATED
    assert decision.reason_code == "SPEND_LIMIT_EXCEEDED"
    assert decision.reason == "Transaction exceeds the configured spending limit"


def test_lower_intent_limit_takes_precedence() -> None:
    decision = make_engine().evaluate(
        make_transaction("1000.01"),
        make_intent(max_amount="1000.00", currency="INR"),
    )

    assert decision.decision == PolicyDecisionType.ESCALATED
    assert decision.reason_code == "SPEND_LIMIT_EXCEEDED"


def test_unsupported_currency_is_escalated() -> None:
    decision = make_engine().evaluate(make_transaction("10.00", currency="USD"), make_intent())

    assert decision.decision == PolicyDecisionType.ESCALATED
    assert decision.reason_code == "UNSUPPORTED_CURRENCY"


def test_blocked_merchant_is_denied() -> None:
    decision = MerchantBlocklistPolicy(frozenset({"merchant-1"})).evaluate(
        make_transaction("50.00"),
        make_intent(),
    )

    assert decision.decision == PolicyDecisionType.DENIED
    assert decision.reason_code == "MERCHANT_BLOCKED"


def test_non_blocked_merchant_is_approved() -> None:
    decision = MerchantBlocklistPolicy(frozenset({"merchant-9"})).evaluate(
        make_transaction("50.00", merchant_id="merchant-1"),
        make_intent(),
    )

    assert decision.decision == PolicyDecisionType.APPROVED


def test_blocked_merchant_precedes_spend_cap() -> None:
    decision = PolicyEngine(
        BlocklistThenSpendCapPolicy(
            blocked_merchant_ids=frozenset({"merchant-1"}),
            spend_cap=SpendCapPolicy(maximum_amount=Decimal("5000.00"), currency="INR"),
        )
    ).evaluate(make_transaction("5000.01"), make_intent())

    assert decision.decision == PolicyDecisionType.DENIED
    assert decision.reason_code == "MERCHANT_BLOCKED"


def test_blocklist_is_case_and_whitespace_insensitive() -> None:
    decision = MerchantBlocklistPolicy(parse_blocked_merchant_ids(" a, B ,,c ")).evaluate(
        make_transaction("50.00", merchant_id=" b "),
        make_intent(),
    )

    assert decision.decision == PolicyDecisionType.DENIED
    assert decision.reason_code == "MERCHANT_BLOCKED"


def test_empty_blocklist_keeps_spend_cap_behavior() -> None:
    decision = PolicyEngine(
        BlocklistThenSpendCapPolicy(
            blocked_merchant_ids=frozenset(),
            spend_cap=SpendCapPolicy(maximum_amount=Decimal("5000.00"), currency="INR"),
        )
    ).evaluate(make_transaction("5000.01"), make_intent())

    assert decision.decision == PolicyDecisionType.ESCALATED
    assert decision.reason_code == "SPEND_LIMIT_EXCEEDED"


def test_parse_blocked_merchant_ids_handles_whitespace_and_case() -> None:
    assert parse_blocked_merchant_ids("a, B ,,c") == frozenset({"a", "b", "c"})
