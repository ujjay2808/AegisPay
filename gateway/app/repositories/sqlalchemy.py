from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.db.models import Agent, Cart, CartItem, Intent, Payment, User
from app.repositories.in_memory import StoredCartRecord, StoredIntentRecord, StoredPaymentRecord
from app.schemas.canonical import CanonicalCart, CanonicalIntent, CanonicalLineItem, CanonicalTransaction
from app.schemas.policy import PolicyDecision, PolicyDecisionType
from app.schemas.state import CartStatus, IntentStatus, PaymentStatus


class SQLAlchemyGatewayRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _commit(self) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def save_intent(self, intent: CanonicalIntent, status: IntentStatus) -> None:
        self._session.merge(User(user_id=intent.user_id))
        self._session.merge(Agent(agent_id=intent.agent_id))
        self._session.add(
            Intent(
                intent_id=intent.intent_id,
                agent_id=intent.agent_id,
                user_id=intent.user_id,
                purpose=intent.purpose,
                status=status.value,
                spending_limit=(intent.spending_constraints.max_amount if intent.spending_constraints else None),
                spending_currency=(intent.spending_constraints.currency if intent.spending_constraints else None),
            )
        )
        self._commit()

    def get_intent(self, intent_id: str) -> StoredIntentRecord | None:
        record = self._session.get(Intent, intent_id)
        if record is None:
            return None
        constraints = None
        if record.spending_limit is not None or record.spending_currency is not None:
            constraints = {
                "max_amount": record.spending_limit,
                "currency": record.spending_currency,
            }
        return StoredIntentRecord(
            intent=CanonicalIntent(
                intent_id=record.intent_id,
                agent_id=record.agent_id,
                user_id=record.user_id,
                purpose=record.purpose,
                spending_constraints=constraints,
            ),
            status=IntentStatus(record.status),
        )

    def save_cart(self, cart: CanonicalCart, status: CartStatus) -> None:
        self._session.add(
            Cart(
                cart_id=cart.cart_id,
                intent_id=cart.intent_id,
                merchant_id=cart.merchant_id,
                merchant_name=cart.merchant_name,
                total=cart.total,
                currency=cart.currency,
                status=status.value,
                items=[
                    CartItem(
                        product_id=item.product_id,
                        name=item.name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        line_total=item.line_total,
                    )
                    for item in cart.items
                ],
            )
        )
        self._commit()

    def get_cart(self, cart_id: str) -> StoredCartRecord | None:
        record = self._session.execute(
            select(Cart).options(joinedload(Cart.items)).where(Cart.cart_id == cart_id)
        ).unique().scalar_one_or_none()
        if record is None:
            return None
        cart = CanonicalCart(
            cart_id=record.cart_id,
            intent_id=record.intent_id,
            merchant_id=record.merchant_id,
            merchant_name=record.merchant_name,
            items=[
                CanonicalLineItem(
                    product_id=item.product_id,
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
                for item in record.items
            ],
            total=record.total,
            currency=record.currency,
        )
        return StoredCartRecord(cart=cart, status=CartStatus(record.status))

    def update_cart_status(self, cart_id: str, status: CartStatus) -> None:
        record = self._session.get(Cart, cart_id)
        if record is None:
            return
        record.status = status.value
        self._commit()

    def save_payment(
        self,
        transaction: CanonicalTransaction,
        status: PaymentStatus,
        decision: PolicyDecision,
    ) -> None:
        self._session.add(
            Payment(
                payment_id=transaction.transaction_id,
                intent_id=transaction.intent_id,
                cart_id=transaction.cart_id,
                agent_id=transaction.agent_id,
                user_id=transaction.user_id,
                merchant_id=transaction.merchant_id,
                merchant_name=transaction.merchant_name,
                amount=transaction.amount,
                currency=transaction.currency,
                payment_method=transaction.payment_method.value,
                idempotency_key=transaction.idempotency_key,
                status=status.value,
                decision=decision.decision.value,
                reason_code=decision.reason_code,
                reason=decision.reason,
            )
        )
        self._commit()

    def get_payment_by_idempotency_key(self, idempotency_key: str) -> StoredPaymentRecord | None:
        record = self._session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if record is None:
            return None
        transaction = CanonicalTransaction(
            transaction_id=record.payment_id,
            intent_id=record.intent_id,
            cart_id=record.cart_id,
            agent_id=record.agent_id,
            user_id=record.user_id,
            merchant_id=record.merchant_id,
            merchant_name=record.merchant_name,
            amount=record.amount,
            currency=record.currency,
            payment_method=record.payment_method,
            idempotency_key=record.idempotency_key,
        )
        decision = PolicyDecision(
            decision=PolicyDecisionType(record.decision),
            reason_code=record.reason_code,
            reason=record.reason,
        )
        return StoredPaymentRecord(transaction=transaction, status=PaymentStatus(record.status), decision=decision)
