import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.mandate_flow import FlowError

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AegisPay Gateway",
    version="0.1.0",
    description="Protocol gateway for AegisPay transaction governance.",
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.exception_handler(FlowError)
async def flow_error_handler(request: Request, error: FlowError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "Request validation failed"},
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed", exc_info=error)
    return JSONResponse(
        status_code=503,
        content={"code": "DATABASE_UNAVAILABLE", "message": "The database operation could not be completed"},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unexpected application error", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
