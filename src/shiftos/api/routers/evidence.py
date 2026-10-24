"""Read-only evidence inspection; acquisition is an explicit administrative CLI."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.core.access import require_api_access
from shiftos.core.errors import DomainError
from shiftos.db.session import get_session
from shiftos.models import (
    AcademicStandard,
    AIImpactEvidence,
    Dataset,
    DatasetVersion,
    EvidenceIngestionJob,
    EvidenceProcessingLog,
    EvidenceReference,
    Occupation,
    OccupationalTask,
    OccupationSkill,
    SDGReference,
    Skill,
    Source,
    WorkforceObservation,
)
from shiftos.schemas.common import ErrorResponse, Page
from shiftos.schemas.evidence import (
    AcademicStandardRead,
    AIImpactEvidenceRead,
    DatasetRead,
    DatasetVersionRead,
    EvidenceIngestionJobRead,
    EvidenceProcessingLogRead,
    EvidenceReferenceRead,
    OccupationalTaskRead,
    OccupationRead,
    OccupationSkillRead,
    ReferenceProvenance,
    SDGReferenceRead,
    SkillRead,
    VersionProvenance,
    WorkforceObservationRead,
)

router = APIRouter(
    prefix="/api/v1/evidence",
    tags=["Reference evidence"],
    dependencies=[Depends(require_api_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 503)},
)
SessionDependency = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Label = Annotated[str | None, Query(max_length=255)]
NORMALIZED_MODELS = (
    Occupation,
    Skill,
    OccupationSkill,
    OccupationalTask,
    WorkforceObservation,
    AIImpactEvidence,
    AcademicStandard,
    SDGReference,
)


def require(session: Session, model, id: UUID):
    record = session.get(model, id)
    if record is None:
        raise DomainError("not_found", f"{model.__name__} was not found", 404)
    return record


def page(session: Session, statement, limit: int, offset: int, order=None) -> dict:
    model = statement.column_descriptions[0]["entity"]
    return {
        "items": session.scalars(
            statement.order_by(*(order or [model.id])).limit(limit).offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(statement.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def reference_query(model, dataset_id, version_id, is_synthetic):
    statement = select(model)
    if dataset_id is not None:
        statement = statement.join(DatasetVersion, model.version_id == DatasetVersion.id).where(
            DatasetVersion.dataset_id == dataset_id
        )
    if version_id is not None:
        statement = statement.where(model.version_id == version_id)
    if is_synthetic is not None:
        statement = statement.where(model.is_synthetic == is_synthetic)
    return statement


def dataset_response(session: Session, dataset: Dataset) -> DatasetRead:
    result = DatasetRead.model_validate(dataset)
    result.latest_ingestion_status = session.scalar(
        select(EvidenceIngestionJob.status)
        .where(EvidenceIngestionJob.dataset_id == dataset.id)
        .order_by(EvidenceIngestionJob.created_at.desc(), EvidenceIngestionJob.id.desc())
        .limit(1)
    )
    return result


def provenance(session: Session, version: DatasetVersion) -> dict:
    return {
        "dataset": dataset_response(session, require(session, Dataset, version.dataset_id)),
        "version": version,
        "source": require(session, Source, version.source_id),
        "record_counts": {
            model.__tablename__: session.scalar(
                select(func.count()).select_from(model).where(model.version_id == version.id)
            )
            or 0
            for model in NORMALIZED_MODELS
        },
    }


@router.get("/datasets", response_model=Page[DatasetRead])
def list_datasets(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    category: Label = None,
    is_synthetic: bool | None = None,
) -> dict:
    statement = select(Dataset)
    if category is not None:
        statement = statement.where(Dataset.category == category)
    if is_synthetic is not None:
        statement = statement.where(Dataset.is_synthetic == is_synthetic)
    result = page(session, statement, limit, offset, [Dataset.registry_key])
    result["items"] = [dataset_response(session, row) for row in result["items"]]
    return result


@router.get("/datasets/{id}", response_model=DatasetRead)
def read_dataset(id: UUID, session: SessionDependency):
    return dataset_response(session, require(session, Dataset, id))


@router.get("/datasets/{id}/versions", response_model=Page[DatasetVersionRead])
def list_versions(id: UUID, session: SessionDependency, limit: Limit = 50, offset: Offset = 0):
    require(session, Dataset, id)
    return page(
        session,
        select(DatasetVersion).where(DatasetVersion.dataset_id == id),
        limit,
        offset,
        [DatasetVersion.retrieved_at.desc(), DatasetVersion.id],
    )


@router.get("/datasets/{id}/jobs", response_model=Page[EvidenceIngestionJobRead])
def list_dataset_jobs(id: UUID, session: SessionDependency, limit: Limit = 50, offset: Offset = 0):
    require(session, Dataset, id)
    return page(
        session,
        select(EvidenceIngestionJob).where(EvidenceIngestionJob.dataset_id == id),
        limit,
        offset,
        [EvidenceIngestionJob.created_at.desc(), EvidenceIngestionJob.id],
    )


@router.get("/versions/{id}", response_model=DatasetVersionRead)
def read_version(id: UUID, session: SessionDependency):
    return require(session, DatasetVersion, id)


@router.get("/versions/{id}/provenance", response_model=VersionProvenance)
def read_version_provenance(id: UUID, session: SessionDependency):
    return provenance(session, require(session, DatasetVersion, id))


@router.get("/references", response_model=Page[EvidenceReferenceRead])
def list_references(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    version_id: UUID | None = None,
    review_status: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(EvidenceReference, None, version_id, is_synthetic)
    if review_status is not None:
        statement = statement.where(EvidenceReference.review_status == review_status)
    return page(session, statement, limit, offset)


@router.get("/references/{id}", response_model=EvidenceReferenceRead)
def read_reference(id: UUID, session: SessionDependency):
    return require(session, EvidenceReference, id)


@router.get("/references/{id}/provenance", response_model=ReferenceProvenance)
def read_reference_provenance(id: UUID, session: SessionDependency):
    evidence = require(session, EvidenceReference, id)
    return {
        **provenance(session, require(session, DatasetVersion, evidence.version_id)),
        "evidence": evidence,
    }


@router.get("/occupations", response_model=Page[OccupationRead])
def list_occupations(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    taxonomy: Label = None,
    q: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(Occupation, dataset_id, version_id, is_synthetic)
    if taxonomy is not None:
        statement = statement.where(Occupation.taxonomy == taxonomy)
    if q is not None:
        statement = statement.where(Occupation.label.icontains(q, autoescape=True))
    return page(session, statement, limit, offset)


@router.get("/occupations/{id}", response_model=OccupationRead)
def read_occupation(id: UUID, session: SessionDependency):
    return require(session, Occupation, id)


@router.get("/occupations/{id}/skills", response_model=Page[OccupationSkillRead])
def list_occupation_skills(
    id: UUID,
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
):
    require(session, Occupation, id)
    result = page(
        session, select(OccupationSkill).where(OccupationSkill.occupation_id == id), limit, offset
    )
    result["items"] = [
        {
            **{key: value for key, value in vars(row).items() if not key.startswith("_")},
            "skill": require(session, Skill, row.skill_id),
        }
        for row in result["items"]
    ]
    return result


@router.get("/occupations/{id}/tasks", response_model=Page[OccupationalTaskRead])
def list_occupation_tasks(
    id: UUID,
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
):
    require(session, Occupation, id)
    return page(
        session, select(OccupationalTask).where(OccupationalTask.occupation_id == id), limit, offset
    )


@router.get("/skills", response_model=Page[SkillRead])
def list_skills(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    taxonomy: Label = None,
    q: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(Skill, dataset_id, version_id, is_synthetic)
    if taxonomy is not None:
        statement = statement.where(Skill.taxonomy == taxonomy)
    if q is not None:
        statement = statement.where(Skill.label.icontains(q, autoescape=True))
    return page(session, statement, limit, offset)


@router.get("/workforce-observations", response_model=Page[WorkforceObservationRead])
def list_workforce_observations(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    indicator: Label = None,
    classification_code: Label = None,
    sector: Label = None,
    geography: Label = None,
    period_start: date | None = None,
    period_end: date | None = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(WorkforceObservation, dataset_id, version_id, is_synthetic)
    for column, value in (
        (WorkforceObservation.indicator, indicator),
        (WorkforceObservation.classification_code, classification_code),
        (WorkforceObservation.sector, sector),
        (WorkforceObservation.geography, geography),
    ):
        if value is not None:
            statement = statement.where(column == value)
    if period_start is not None:
        statement = statement.where(WorkforceObservation.period_start >= period_start)
    if period_end is not None:
        statement = statement.where(WorkforceObservation.period_end <= period_end)
    return page(
        session,
        statement,
        limit,
        offset,
        [WorkforceObservation.period_start, WorkforceObservation.id],
    )


@router.get("/ai-impact", response_model=Page[AIImpactEvidenceRead])
def list_ai_impact(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    impact_type: Label = None,
    occupation_label: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(AIImpactEvidence, dataset_id, version_id, is_synthetic)
    if impact_type is not None:
        statement = statement.where(AIImpactEvidence.impact_type == impact_type)
    if occupation_label is not None:
        statement = statement.where(AIImpactEvidence.occupation_label == occupation_label)
    return page(session, statement, limit, offset)


@router.get("/academic-standards", response_model=Page[AcademicStandardRead])
def list_academic_standards(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    discipline: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(AcademicStandard, dataset_id, version_id, is_synthetic)
    if discipline is not None:
        statement = statement.where(AcademicStandard.discipline == discipline)
    return page(session, statement, limit, offset)


@router.get("/sdg-references", response_model=Page[SDGReferenceRead])
def list_sdg_references(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    version_id: UUID | None = None,
    kind: Label = None,
    goal_code: Label = None,
    is_synthetic: bool | None = None,
):
    statement = reference_query(SDGReference, dataset_id, version_id, is_synthetic)
    if kind is not None:
        statement = statement.where(SDGReference.kind == kind)
    if goal_code is not None:
        statement = statement.where(SDGReference.goal_code == goal_code)
    return page(session, statement, limit, offset)


@router.get("/ingestion-jobs", response_model=Page[EvidenceIngestionJobRead])
def list_ingestion_jobs(
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    dataset_id: UUID | None = None,
    status: Label = None,
):
    statement = select(EvidenceIngestionJob)
    if dataset_id is not None:
        statement = statement.where(EvidenceIngestionJob.dataset_id == dataset_id)
    if status is not None:
        statement = statement.where(EvidenceIngestionJob.status == status)
    return page(
        session,
        statement,
        limit,
        offset,
        [EvidenceIngestionJob.created_at.desc(), EvidenceIngestionJob.id],
    )


@router.get("/ingestion-jobs/{id}", response_model=EvidenceIngestionJobRead)
def read_ingestion_job(id: UUID, session: SessionDependency):
    return require(session, EvidenceIngestionJob, id)


@router.get("/ingestion-jobs/{id}/logs", response_model=Page[EvidenceProcessingLogRead])
def list_processing_logs(
    id: UUID,
    session: SessionDependency,
    limit: Limit = 50,
    offset: Offset = 0,
):
    require(session, EvidenceIngestionJob, id)
    return page(
        session,
        select(EvidenceProcessingLog).where(EvidenceProcessingLog.job_id == id),
        limit,
        offset,
        [EvidenceProcessingLog.created_at, EvidenceProcessingLog.id],
    )
