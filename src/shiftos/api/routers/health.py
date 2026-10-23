from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shiftos.core.errors import DomainError
from shiftos.schemas.common import ErrorResponse, HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def ready(request: Request) -> HealthResponse:
    try:
        with request.app.state.database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise DomainError(
            "DATABASE_UNAVAILABLE", "Database is unavailable", status_code=503
        ) from None
    return HealthResponse(status="ready")
