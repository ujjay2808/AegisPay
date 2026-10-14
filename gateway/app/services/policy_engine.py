from decimal import Decimal

from app.core.config import Settings, parse_blocked_merchant_ids
from app.schemas.canonical import CanonicalIntent, CanonicalTransaction
from app.schemas.policy import PolicyDecision, PolicyDecisionType


class SpendCapPolicy:
    def __init__(self, *, maximum_amount: Decimal, currency: str) -> None:
        self._maximum_amount = maximum_amount
        self._currency = currency.upper()

    def evaluate(
        self,
        transaction: CanonicalTransaction,
        intent: CanonicalIntent,
    ) -> PolicyDecision:
        if transaction.currency != self._currency:
            return PolicyDecision(
                decision=PolicyDecisionType.ESCALATED,
                reason_code="UNSUPPORTED_CURRENCY",
                reason=(
                    f"No spend-cap conversion is configured for {transaction.currency}; "
                    "transaction requires review"
                ),
            )

        maximum_amount = self._maximum_amount
        constraints = intent.spending_constraints
        if constraints is not None and constraints.currency not in (None, transaction.currency):
            return PolicyDecision(
                decision=PolicyDecisionType.ESCALATED,
                reason_code="INTENT_CURRENCY_MISMATCH",
                reason="Intent spending constraint currency does not match the transaction currency",
            )
        if constraints is not None and constraints.max_amount is not None:
            maximum_amount = min(maximum_amount, constraints.max_amount)

        if transaction.amount <= maximum_amount:
            return PolicyDecision(
                decision=PolicyDecisionType.APPROVED,
                reason_code="WITHIN_SPEND_LIMIT",
                reason="Transaction is within the configured spending limit",
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ESCALATED,
            reason_code="SPEND_LIMIT_EXCEEDED",
            reason="Transaction exceeds the configured spending limit",
        )


class MerchantBlocklistPolicy:
    def __init__(self, blocked_merchant_ids: frozenset[str]) -> None:
        self._blocked_merchant_ids = blocked_merchant_ids

    def evaluate(
        self,
        transaction: CanonicalTransaction,
        intent: CanonicalIntent,
    ) -> PolicyDecision:
        normalized_merchant = transaction.merchant_id.strip().casefold()
        if normalized_merchant in self._blocked_merchant_ids:
            return PolicyDecision(
                decision=PolicyDecisionType.DENIED,
                reason_code="MERCHANT_BLOCKED",
                reason=f"Merchant {transaction.merchant_id} is blocked from processing",
            )
        return PolicyDecision(
            decision=PolicyDecisionType.APPROVED,
            reason_code="MERCHANT_ALLOWED",
            reason="Merchant is not blocked",
        )


class BlocklistThenSpendCapPolicy:
    def __init__(self, *, blocked_merchant_ids: frozenset[str], spend_cap: SpendCapPolicy) -> None:
        self._blocked_merchant_ids = blocked_merchant_ids
        self._blocklist_policy = MerchantBlocklistPolicy(blocked_merchant_ids)
        self._spend_cap = spend_cap

    def evaluate(
        self,
        transaction: CanonicalTransaction,
        intent: CanonicalIntent,
    ) -> PolicyDecision:
        blocklist_decision = self._blocklist_policy.evaluate(transaction, intent)
        if blocklist_decision.decision == PolicyDecisionType.DENIED:
            return blocklist_decision
        return self._spend_cap.evaluate(transaction, intent)


class PolicyEngine:
    def __init__(self, spend_cap: SpendCapPolicy | MerchantBlocklistPolicy | BlocklistThenSpendCapPolicy) -> None:
        self._spend_cap = spend_cap

    def evaluate(
        self,
        transaction: CanonicalTransaction,
        intent: CanonicalIntent,
    ) -> PolicyDecision:
        return self._spend_cap.evaluate(transaction, intent)


def get_policy_engine(settings: Settings) -> PolicyEngine:
    spend_cap = SpendCapPolicy(
        maximum_amount=settings.spend_cap_amount,
        currency=settings.spend_cap_currency,
    )
    blocked_merchant_ids = parse_blocked_merchant_ids(settings.blocked_merchant_ids)
    return PolicyEngine(
        BlocklistThenSpendCapPolicy(
            blocked_merchant_ids=blocked_merchant_ids,
            spend_cap=spend_cap,
        )
    )
