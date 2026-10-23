from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: Literal["alive", "ready"]


T = TypeVar("T")


class Page(BaseModel, Generic[T]):  # noqa: UP046 - preserve the tested Pydantic generic contract
    items: list[T]
    total: int
    limit: int
    offset: int
