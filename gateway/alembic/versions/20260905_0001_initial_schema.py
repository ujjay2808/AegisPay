"""Create initial gateway schema.

Revision ID: 20260905_0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260905_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("agents", sa.Column("agent_id", sa.String(128), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("users", sa.Column("user_id", sa.String(128), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("policies", sa.Column("policy_id", sa.Integer, primary_key=True), sa.Column("policy_type", sa.String(64), nullable=False, unique=True), sa.Column("maximum_amount", sa.Numeric(18, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("intents", sa.Column("intent_id", sa.String(128), primary_key=True), sa.Column("agent_id", sa.String(128), sa.ForeignKey("agents.agent_id"), nullable=False), sa.Column("user_id", sa.String(128), sa.ForeignKey("users.user_id"), nullable=False), sa.Column("purpose", sa.Text, nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("spending_limit", sa.Numeric(18, 2)), sa.Column("spending_currency", sa.String(3)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_intents_user_id", "intents", ["user_id"])
    op.create_index("ix_intents_agent_id", "intents", ["agent_id"])
    op.create_table("carts", sa.Column("cart_id", sa.String(128), primary_key=True), sa.Column("intent_id", sa.String(128), sa.ForeignKey("intents.intent_id"), nullable=False), sa.Column("merchant_id", sa.String(128), nullable=False), sa.Column("merchant_name", sa.String(255), nullable=False), sa.Column("total", sa.Numeric(18, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_carts_intent_id", "carts", ["intent_id"])
    op.create_table("cart_items", sa.Column("id", sa.Integer, primary_key=True), sa.Column("cart_id", sa.String(128), sa.ForeignKey("carts.cart_id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", sa.String(128), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("quantity", sa.Integer, nullable=False), sa.Column("unit_price", sa.Numeric(18, 2), nullable=False), sa.Column("line_total", sa.Numeric(18, 2), nullable=False))
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_table("payments", sa.Column("payment_id", sa.String(128), primary_key=True), sa.Column("intent_id", sa.String(128), sa.ForeignKey("intents.intent_id"), nullable=False), sa.Column("cart_id", sa.String(128), sa.ForeignKey("carts.cart_id"), nullable=False), sa.Column("agent_id", sa.String(128), nullable=False), sa.Column("user_id", sa.String(128), nullable=False), sa.Column("merchant_id", sa.String(128), nullable=False), sa.Column("merchant_name", sa.String(255), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("payment_method", sa.String(32), nullable=False), sa.Column("idempotency_key", sa.String(255), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("reason_code", sa.String(64), nullable=False), sa.Column("reason", sa.Text, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("idempotency_key"))
    op.create_index("ix_payments_cart_id", "payments", ["cart_id"])
    op.create_index("ix_payments_intent_id", "payments", ["intent_id"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index("ix_carts_intent_id", table_name="carts")
    op.drop_table("carts")
    op.drop_index("ix_intents_agent_id", table_name="intents")
    op.drop_index("ix_intents_user_id", table_name="intents")
    op.drop_table("intents")
    op.drop_table("policies")
    op.drop_table("users")
    op.drop_table("agents")
