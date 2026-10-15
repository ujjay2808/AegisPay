from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Cart, CartItem, Intent, Payment
from app.repositories.sqlalchemy import SQLAlchemyGatewayRepository
from app.schemas.canonical import CanonicalCart, CanonicalIntent, CanonicalLineItem, CanonicalTransaction
from app.schemas.payment import SimulatedPaymentMethod
from app.schemas.policy import PolicyDecision, PolicyDecisionType
from app.schemas.state import CartStatus, IntentStatus, PaymentStatus


def test_sqlalchemy_repository_persists_relationships_and_idempotency() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SQLAlchemyGatewayRepository(session)
        intent = CanonicalIntent(
            intent_id="intent-db-1",
            agent_id="agent-db-1",
            user_id="user-db-1",
            purpose="Database test",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        )
        cart = CanonicalCart(
            cart_id="cart-db-1",
            intent_id=intent.intent_id,
            merchant_id="merchant-db-1",
            merchant_name="Database Merchant",
            items=[CanonicalLineItem(product_id="product-db-1", name="Item", quantity=2, unit_price="10.00", line_total="20.00")],
            total="20.00",
            currency="INR",
        )
        transaction = CanonicalTransaction(
            transaction_id="payment-db-1",
            intent_id=intent.intent_id,
            cart_id=cart.cart_id,
            agent_id=intent.agent_id,
            user_id=intent.user_id,
            merchant_id=cart.merchant_id,
            merchant_name=cart.merchant_name,
            amount=cart.total,
            currency=cart.currency,
            payment_method=SimulatedPaymentMethod.SIMULATED_CARD,
            idempotency_key="db-key-1",
        )
        decision = PolicyDecision(
            decision=PolicyDecisionType.APPROVED,
            reason_code="WITHIN_SPEND_LIMIT",
            reason="Transaction is within the configured spending limit",
        )

        repository.save_intent(intent, IntentStatus.ACTIVE)
        repository.save_cart(cart, CartStatus.READY_FOR_PAYMENT)
        repository.save_payment(transaction, PaymentStatus.APPROVED, decision, audit_tx_hash="0xabc123")
        repository.update_cart_status(cart.cart_id, CartStatus.PAYMENT_PENDING)

        stored_intent = repository.get_intent(intent.intent_id)
        stored_cart = repository.get_cart(cart.cart_id)
        stored_payment = repository.get_payment_by_idempotency_key("db-key-1")

        assert stored_intent is not None
        assert stored_intent.intent.intent_id == intent.intent_id
        assert stored_cart is not None
        assert stored_cart.cart.total == Decimal("20.00")
        assert stored_cart.status == CartStatus.PAYMENT_PENDING
        assert stored_payment is not None
        assert stored_payment.decision.reason_code == "WITHIN_SPEND_LIMIT"
        assert stored_payment.audit_tx_hash == "0xabc123"

        assert session.scalar(select(Intent).where(Intent.intent_id == intent.intent_id)) is not None
        assert session.scalar(select(CartItem).where(CartItem.cart_id == cart.cart_id)) is not None
        assert session.scalar(select(Payment).where(Payment.idempotency_key == "db-key-1")) is not None


def test_sqlalchemy_repository_persists_denied_status() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SQLAlchemyGatewayRepository(session)
        intent = CanonicalIntent(
            intent_id="intent-db-denied",
            agent_id="agent-db-denied",
            user_id="user-db-denied",
            purpose="Denied database test",
            spending_constraints={"max_amount": "5000", "currency": "INR"},
        )
        cart = CanonicalCart(
            cart_id="cart-db-denied",
            intent_id=intent.intent_id,
            merchant_id="blocked-merchant",
            merchant_name="Blocked Merchant",
            items=[CanonicalLineItem(product_id="product-db-denied", name="Denied Item", quantity=1, unit_price="10.00", line_total="10.00")],
            total="10.00",
            currency="INR",
        )
        transaction = CanonicalTransaction(
            transaction_id="payment-db-denied",
            intent_id=intent.intent_id,
            cart_id=cart.cart_id,
            agent_id=intent.agent_id,
            user_id=intent.user_id,
            merchant_id=cart.merchant_id,
            merchant_name=cart.merchant_name,
            amount=cart.total,
            currency=cart.currency,
            payment_method=SimulatedPaymentMethod.SIMULATED_CARD,
            idempotency_key="db-key-denied",
        )
        decision = PolicyDecision(
            decision=PolicyDecisionType.DENIED,
            reason_code="MERCHANT_BLOCKED",
            reason="Merchant blocked-merchant is blocked from processing",
        )

        repository.save_intent(intent, IntentStatus.ACTIVE)
        repository.save_cart(cart, CartStatus.READY_FOR_PAYMENT)
        repository.save_payment(transaction, PaymentStatus.DENIED, decision, audit_tx_hash="0xdenied")

        stored_payment = repository.get_payment_by_idempotency_key("db-key-denied")

        assert stored_payment is not None
        assert stored_payment.status == PaymentStatus.DENIED
        assert stored_payment.decision.decision == PolicyDecisionType.DENIED
        assert stored_payment.decision.reason_code == "MERCHANT_BLOCKED"
        assert stored_payment.audit_tx_hash == "0xdenied"
