from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.repositories.sqlalchemy import SQLAlchemyGatewayRepository
from app.services.audit_client import AuditClient
from app.services.mandate_flow import MandateFlowService
from app.services.normalization import get_ap2_normalization_service
from app.services.policy_engine import get_policy_engine


def get_mandate_flow(db: Session = Depends(get_db)) -> Generator[MandateFlowService, None, None]:
    audit_client = None
    if settings.audit_enabled:
        audit_client = AuditClient(
            audit_service_url=settings.audit_service_url,
            timeout_seconds=settings.audit_timeout_seconds,
        )

    yield MandateFlowService(
        repository=SQLAlchemyGatewayRepository(db),
        normalization=get_ap2_normalization_service(),
        policy_engine=get_policy_engine(settings),
        audit_client=audit_client,
    )
