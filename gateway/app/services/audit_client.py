import hashlib
import json
import logging
import time
from typing import Optional

import httpx

from app.schemas.canonical import CanonicalTransaction
from app.schemas.policy import PolicyDecision


logger = logging.getLogger(__name__)


class AuditClient:
    def __init__(
        self,
        *,
        audit_service_url: str,
        timeout_seconds: float,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._audit_service_url = audit_service_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def record_decision(self, transaction: CanonicalTransaction, decision: PolicyDecision) -> Optional[str]:
        started_at = time.perf_counter()
        try:
            payload = self._build_payload(transaction, decision)
            with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = client.post(
                    f"{self._audit_service_url}/api/decisions",
                    json=payload,
                )

            elapsed_ms = (time.perf_counter() - started_at) * 1000
            if not response.is_success:
                logger.warning(
                    "Audit decision request failed with status %s for transaction %s in %.2fms",
                    response.status_code,
                    transaction.transaction_id,
                    elapsed_ms,
                )
                return None

            try:
                body = response.json()
            except ValueError:
                logger.warning(
                    "Audit decision response had invalid JSON for transaction %s in %.2fms",
                    transaction.transaction_id,
                    elapsed_ms,
                )
                return None

            tx_hash = body.get("txHash") if isinstance(body, dict) else None
            if not isinstance(tx_hash, str):
                logger.warning(
                    "Audit decision response missing txHash for transaction %s in %.2fms",
                    transaction.transaction_id,
                    elapsed_ms,
                )
                return None

            logger.info(
                "Audit decision recorded for transaction %s in %.2fms",
                transaction.transaction_id,
                elapsed_ms,
            )
            return tx_hash
        except Exception as error:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.warning(
                "Audit decision request raised %s for transaction %s in %.2fms",
                type(error).__name__,
                transaction.transaction_id,
                elapsed_ms,
            )
            return None

    @staticmethod
    def _build_payload(transaction: CanonicalTransaction, decision: PolicyDecision) -> dict[str, str]:
        canonical_json = json.dumps(
            {
                "transaction_id": transaction.transaction_id,
                "cart_id": transaction.cart_id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "decision": decision.decision.value,
                "reason_code": decision.reason_code,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        decision_hash = "0x" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return {
            "decisionHash": decision_hash,
            "decision": decision.decision.value,
        }
