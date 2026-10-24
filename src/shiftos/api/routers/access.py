"""Authenticated current grants only; no credentials, policy internals or DB work."""

from fastapi import APIRouter, Depends, Request

from shiftos.core.access import BEARER, authenticate
from shiftos.schemas.access import AccessContext, ExecutionConfiguration
from shiftos.schemas.common import ErrorResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Workspace access"],
    dependencies=[Depends(BEARER)],
    responses={code: {"model": ErrorResponse} for code in (401, 503)},
)


@router.get("/access-context", response_model=AccessContext)
def access_context(request: Request) -> AccessContext:
    # Own-grant inspection is available even to an authenticated write-only grant;
    # it never grants read access to institution records or implies other rights.
    principal = authenticate(request)
    settings = request.app.state.settings
    execution = ExecutionConfiguration(
        external_processing_allowed=settings.analysis_external_processing_allowed,
        research_enabled=settings.research_enabled,
        claude_enabled=settings.claude_enabled,
    )
    limitations = [
        "An operator grant does not establish named academic identity or committee approval.",
        "Configuration flags are not billing consent, provider acceptance or worker availability.",
    ]
    if principal is None:
        return AccessContext(
            access_mode="legacy",
            authenticated=False,
            operator_alias=None,
            identity_kind="unconfigured_legacy",
            permissions=[],
            institution_ids=[],
            global_admin=False,
            execution=execution,
            limitations=[
                "Legacy development headers do not establish a scoped workspace context; "
                "configure scoped access before using authenticated preview controls.",
                *limitations,
            ],
        )
    return AccessContext(
        access_mode="scoped",
        authenticated=True,
        operator_alias=principal.principal_id,
        identity_kind="operator_grant",
        permissions=[
            permission
            for permission in ("read", "write", "review", "admin")
            if permission in principal.permissions
        ],
        institution_ids=sorted(principal.institution_ids),
        global_admin="admin" in principal.permissions,
        execution=execution,
        limitations=limitations,
    )
