from fastapi import APIRouter, Depends, status
from typing import Annotated

from app.api.dependencies import get_mandate_flow
from app.services.mandate_flow import MandateFlowService
from app.schemas.cart import CartCreateRequest, CartCreateResponse
from app.schemas.errors import ErrorResponse
from app.schemas.intent import IntentCreateRequest, IntentCreateResponse
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse

router = APIRouter(prefix="/mandates", tags=["mandates"])


@router.post(
    "/intent",
    response_model=IntentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={500: {"model": ErrorResponse}},
)
def create_intent(
    request: IntentCreateRequest,
    flow: Annotated[MandateFlowService, Depends(get_mandate_flow)],
) -> IntentCreateResponse:
    intent, intent_status = flow.create_intent(request)
    return IntentCreateResponse(
        intent_id=intent.intent_id,
        agent_id=intent.agent_id,
        user_id=intent.user_id,
        status=intent_status,
    )


@router.post(
    "/cart",
    response_model=CartCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_cart(
    request: CartCreateRequest,
    flow: Annotated[MandateFlowService, Depends(get_mandate_flow)],
) -> CartCreateResponse:
    cart, cart_status = flow.create_cart(request)
    return CartCreateResponse(
        cart_id=cart.cart_id,
        intent_id=cart.intent_id,
        total={"amount": cart.total, "currency": cart.currency},
        status=cart_status,
    )


@router.post(
    "/payment",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_payment(
    request: PaymentCreateRequest,
    flow: Annotated[MandateFlowService, Depends(get_mandate_flow)],
) -> PaymentCreateResponse:
    transaction, payment_status, decision = flow.create_payment(request)
    return PaymentCreateResponse(
        payment_id=transaction.transaction_id,
        cart_id=transaction.cart_id,
        decision=decision.decision,
        status=payment_status,
        reason_code=decision.reason_code,
        reason=decision.reason,
    )
