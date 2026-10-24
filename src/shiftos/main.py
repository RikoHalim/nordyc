import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from shiftos import __version__
from shiftos.api.body_limit import BodyLimitMiddleware
from shiftos.api.routers import academic, catalogue, evidence, health, workforce_radar
from shiftos.core.config import Settings
from shiftos.core.errors import DomainError
from shiftos.db.session import Database, create_database

logger = logging.getLogger("shiftos.http")


def error_response(code: str, message: str, status_code: int, details: list | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings()
    owns_database = database is None
    database = database or create_database(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if owns_database:
                database.engine.dispose()

    application = FastAPI(title="SHIFT//OS", version=__version__, lifespan=lifespan)
    application.state.settings = settings
    application.state.database = database

    @application.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code, exc.details)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "type": item["type"], "message": "Invalid value"}
            for item in exc.errors()
        ]
        return error_response("VALIDATION_ERROR", "Request validation failed", 422, details)

    @application.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return error_response(code, str(exc.detail), exc.status_code)

    @application.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, _exc: IntegrityError) -> JSONResponse:
        return error_response("CONFLICT", "The record conflicts with stored data", 409)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return error_response("DATABASE_UNAVAILABLE", "Database is unavailable", 503)

    @application.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.error(json.dumps({"event": "request_failed", "exception_type": type(exc).__name__}))
        return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)

    @application.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = str(uuid4())
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status_code": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    application.include_router(health.router)
    application.include_router(academic.router)
    application.include_router(evidence.router)
    application.include_router(workforce_radar.router)
    application.include_router(catalogue.router)
    application.add_middleware(BodyLimitMiddleware)
    return application


app = create_app()
