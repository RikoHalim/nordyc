from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shiftos.core.errors import DomainError
from shiftos.schemas.common import ErrorResponse, HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def ready(request: Request) -> HealthResponse:
    if request.app.state.settings.app_env == "production":
        from shiftos.core.access import validate_access_configuration

        validate_access_configuration(request.app.state.settings)
    try:
        with request.app.state.database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if request.app.state.settings.app_env == "production":
                from shiftos.services.runtime import migration_heads

                actual = sorted(
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
                )
                if actual != migration_heads():
                    raise DomainError("SCHEMA_NOT_READY", "Apply reviewed database migrations", 503)
    except SQLAlchemyError:
        raise DomainError(
            "DATABASE_UNAVAILABLE", "Database is unavailable", status_code=503
        ) from None
    return HealthResponse(status="ready")
