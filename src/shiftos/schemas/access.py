"""Safe operator capabilities for a controlled preview, not a named identity."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shiftos.core.access import Permission


class ExecutionConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_processing_allowed: bool
    research_enabled: bool
    claude_enabled: bool


class AccessContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_mode: Literal["scoped", "legacy"]
    authenticated: bool
    operator_alias: str | None = Field(
        description="Configured operator-grant alias; this is not named academic identity."
    )
    identity_kind: Literal["operator_grant", "unconfigured_legacy"]
    permissions: list[Permission]
    institution_ids: list[UUID]
    global_admin: bool
    execution: ExecutionConfiguration
    limitations: list[str]
