from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shiftos.core.access import require_api_access
from shiftos.db.session import get_session
from shiftos.schemas.common import ErrorResponse
from shiftos.schemas.workforce_radar import (
    AITransformationResult,
    TrendPolicy,
    WorkforceTrendResult,
)
from shiftos.services.evidence.trends import compare_observations, occupation_ai_transformation

router = APIRouter(
    prefix="/api/v1/evidence",
    tags=["Future Workforce Radar"],
    dependencies=[Depends(require_api_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 503)},
)
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/workforce-trends", response_model=WorkforceTrendResult)
def workforce_trend(
    before_id: UUID,
    after_id: UUID,
    session: SessionDependency,
    percent_threshold: Annotated[Decimal, Query(ge=0, le=1000, allow_inf_nan=False)] = Decimal("5"),
    absolute_threshold: Annotated[Decimal, Query(ge=0, le=10**18, allow_inf_nan=False)] = Decimal(
        "0"
    ),
) -> WorkforceTrendResult:
    return compare_observations(
        session,
        before_id,
        after_id,
        TrendPolicy(
            percent_threshold=percent_threshold,
            absolute_threshold=absolute_threshold,
        ),
    )


@router.get("/occupations/{id}/ai-transformation", response_model=AITransformationResult)
def occupation_transformation(id: UUID, session: SessionDependency) -> AITransformationResult:
    return occupation_ai_transformation(session, id)
