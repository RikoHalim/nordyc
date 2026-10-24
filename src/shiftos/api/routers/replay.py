"""Protected explicit change assessment; no job execution or source-content output."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from shiftos.api.routers.analysis import SessionDep, require_analysis_access
from shiftos.core.access import require_api_access
from shiftos.schemas.common import ErrorResponse
from shiftos.schemas.replay import ReplayAssessment, ReplayRequest
from shiftos.services.replay import assess_replay

router = APIRouter(
    prefix="/api/v1",
    tags=["Explicit change replay"],
    dependencies=[Depends(require_api_access), Depends(require_analysis_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)},
)


@router.post("/programmes/{programme_id}/replay-assessment", response_model=ReplayAssessment)
def replay_assessment(
    programme_id: UUID, payload: ReplayRequest, request: Request, session: SessionDep
):
    return assess_replay(session, programme_id, payload, request.app.state.settings)
