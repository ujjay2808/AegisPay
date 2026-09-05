from enum import StrEnum


class IntentStatus(StrEnum):
    ACTIVE = "ACTIVE"


class CartStatus(StrEnum):
    READY_FOR_PAYMENT = "READY_FOR_PAYMENT"
    PAYMENT_PENDING = "PAYMENT_PENDING"


class PaymentStatus(StrEnum):
    APPROVED = "APPROVED"
    ESCALATED = "ESCALATED"
    DENIED = "DENIED"
