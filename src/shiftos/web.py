"""Explicit same-origin built frontend and opt-in, frozen synthetic read access.

This entrypoint never migrates, seeds, installs mocks or grants anonymous writes.
The ordinary FastAPI factory remains unchanged and protected.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from time import time
from uuid import UUID

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from starlette.concurrency import run_in_threadpool

from shiftos import public_uploads
from shiftos.api.body_limit import BodyLimitMiddleware
from shiftos.api.routers.analysis import analysis_response
from shiftos.api.routers.career import career_response
from shiftos.api.routers.pathways import plan_response
from shiftos.core.access import AccessPolicy, _policy, validate_access_configuration
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.db.session import Database, create_database
from shiftos.models import (
    ActionPlanRun,
    AnalysisRun,
    CareerRun,
    Course,
    CourseFinding,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
)
from shiftos.schemas.analysis import ProgrammeResult
from shiftos.schemas.career import CareerResult
from shiftos.schemas.pathways import PlanResult
from shiftos.services.ingestion.worker import run_once

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger("shiftos.web")
MATERIALISED_POLICIES: set[Path] = set()
SCHEMA = re.compile(r"[a-z_][a-z0-9_]{0,62}")
SPA = re.compile(
    r"(?:|help|access|programmes/[a-fA-F0-9-]{36}/"
    r"(?:overview|courses|industry|careers|competencies|recommendations|pathways|"
    r"scenarios|sdg|plan|reviews|evidence|settings|upload))/?"
)
HASHED_ASSET = re.compile(r".+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+")
ASSET_TYPES = {
    ".js",
    ".css",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".avif",
    ".ico",
}


@dataclass(frozen=True)
class WebOptions:
    dist: Path = ROOT / "frontend" / "dist"
    schema: str | None = None
    public_enabled: bool = False
    public_institution_id: UUID | None = None
    public_programme_id: UUID | None = None
    public_principal_id: str | None = None
    worker_enabled: bool = False
    public_uploads_enabled: bool = False

    @classmethod
    def from_env(cls):
        def flag(key):
            value = os.environ.get(key, "false").lower()
            if value not in {"true", "false"}:
                raise ValueError("Web flags require explicit true or false values")
            return value == "true"

        def identity(key):
            value = os.environ.get(key)
            return UUID(value) if value else None

        return cls(
            dist=Path(os.environ.get("NORDYC_DIST_DIR", str(ROOT / "frontend/dist"))),
            schema=os.environ.get("NORDYC_DATABASE_SCHEMA") or None,
            public_enabled=flag("NORDYC_PUBLIC_DEMO_ENABLED"),
            public_institution_id=identity("NORDYC_PUBLIC_INSTITUTION_ID"),
            public_programme_id=identity("NORDYC_PUBLIC_PROGRAMME_ID"),
            public_principal_id=os.environ.get("NORDYC_PUBLIC_PRINCIPAL_ID") or None,
            worker_enabled=flag("NORDYC_WORKER_ENABLED"),
            public_uploads_enabled=flag("NORDYC_PUBLIC_UPLOADS_ENABLED"),
        )


def deployment_settings() -> Settings:
    """Read a secret policy without printing it or writing inside static assets."""
    supplied = os.environ.get("NORDYC_ACCESS_POLICY_JSON")
    if supplied is None:
        return Settings()
    if len(supplied.encode("utf-8")) > 100_000:
        raise ValueError("Configure a bounded valid access policy")
    try:
        policy = AccessPolicy.model_validate_json(supplied)
    except ValueError:
        raise ValueError("Configure a bounded valid access policy") from None
    directory = Path(tempfile.mkdtemp(prefix="shiftos-web-policy-"))
    directory.chmod(0o700)
    path = directory / "access-policy.private.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(policy.model_dump_json())
    MATERIALISED_POLICIES.add(path)
    return Settings(api_access_policy_path=path)


def _public_principal(settings, database, options):
    """Fail closed on scope drift, source withdrawal or missing saved results."""
    if (
        not options.public_enabled
        or settings.api_access_mode != "scoped"
        or not options.public_institution_id
        or not options.public_programme_id
        or not options.public_principal_id
        or settings.analysis_external_processing_allowed
        or settings.research_enabled
        or settings.gemini_enabled
        or settings.analysis_gemini_fallback_enabled
    ):
        raise ValueError("Public preview requires explicit isolated synthetic read-only settings")
    principal = next(
        (
            row
            for row in _policy(settings).principals
            if row.principal_id == options.public_principal_id
        ),
        None,
    )
    if (
        principal is None
        or principal.permissions != frozenset({"read"})
        or principal.institution_ids != frozenset({options.public_institution_id})
    ):
        raise ValueError("Public preview requires an exact existing read-only institution grant")
    with database.session_factory() as session:
        institution = session.get(Institution, options.public_institution_id)
        programme = session.get(Programme, options.public_programme_id)
        if (
            not institution
            or not institution.is_synthetic
            or not programme
            or not programme.is_synthetic
            or programme.institution_id != institution.id
            or not programme.active_revision_id
            or session.scalar(
                select(func.count())
                .select_from(Programme)
                .where(Programme.institution_id == institution.id)
            )
            != 1
        ):
            raise ValueError("The public target must contain exactly one fictional programme")
        if session.scalar(
            select(func.count())
            .select_from(ProgrammeRevision)
            .where(
                ProgrammeRevision.programme_id == programme.id,
                ProgrammeRevision.is_synthetic.is_(False),
            )
        ):
            raise ValueError("Every public programme revision must remain explicitly fictional")
        courses = session.scalars(
            select(Course)
            .join(ProgrammeRevision, Course.programme_revision_id == ProgrammeRevision.id)
            .where(ProgrammeRevision.programme_id == programme.id)
            .limit(2)
        ).all()
        if (
            len(courses) != 1
            or not courses[0].is_synthetic
            or courses[0].programme_revision_id != programme.active_revision_id
        ):
            raise ValueError("The public target must contain exactly one fictional course")
        selected = {}
        for name, model, response in (
            ("analysis", AnalysisRun, analysis_response),
            ("career", CareerRun, career_response),
            ("plan", ActionPlanRun, plan_response),
        ):
            runs = session.scalars(
                select(model)
                .join(Job, model.job_id == Job.id)
                .where(
                    model.programme_id == programme.id,
                    model.programme_revision_id == programme.active_revision_id,
                    Job.institution_id == institution.id,
                    Job.programme_revision_id == programme.active_revision_id,
                    Job.is_synthetic.is_(True),
                    Job.status.in_([JobStatus.SUCCEEDED, JobStatus.PARTIAL]),
                )
                .order_by(model.created_at.desc())
                .limit(1)
            ).all()
            if not runs or not runs[0].is_synthetic or not runs[0].fingerprint:
                raise ValueError("Saved completed synthetic findings are required")
            run = runs[0]
            if response(session, run, settings).get("needs_evidence_revalidation") is not False:
                raise ValueError("Public findings require current explicit source permissions")
            selected[name] = run
        career, plan = selected["career"], selected["plan"]
        findings = session.scalars(
            select(CourseFinding).where(CourseFinding.run_id == selected["analysis"].id).limit(2)
        ).all()
        if (
            len(findings) != 1
            or not findings[0].is_synthetic
            or findings[0].course_id != courses[0].id
            or findings[0].programme_revision_id != programme.active_revision_id
        ):
            raise ValueError("A committed finding is required for the exact fictional course")
        try:
            analysis_result = ProgrammeResult.model_validate(
                {**selected["analysis"].summary_json, "courses": [findings[0].result_json]}
            )
            career_result = CareerResult.model_validate(career.result_json)
            plan_result = PlanResult.model_validate(plan.result_json)
        except ValueError:
            raise ValueError("Saved public findings do not satisfy the result schemas") from None
        if (
            plan.career_run_id != career.id
            or plan.career_fingerprint != career.fingerprint
            or plan_result.career_run_id != career.id
            or plan_result.career_fingerprint != career.fingerprint
            or career_result.programme_id != programme.id
            or plan_result.programme_id != programme.id
            or career_result.programme_revision_id != programme.active_revision_id
            or plan_result.programme_revision_id != programme.active_revision_id
            or not career_result.is_synthetic
            or not plan_result.is_synthetic
            or not analysis_result.is_synthetic
            or analysis_result.programme_revision_id != programme.active_revision_id
            or analysis_result.summary.inventory_count != 1
            or analysis_result.summary.returned_count != 1
            or set(career_result.course_ids) != {courses[0].id}
            or set(plan_result.overview.course_ids) != {courses[0].id}
        ):
            raise ValueError("Saved results must retain exact synthetic lineage")
    return principal


class WebWorker:
    """Optional ordinary worker; never installs mock providers or retries failed jobs."""

    def __init__(self, database, settings, *, public_uploads_only=False):
        self.database, self.settings = database, settings
        self.public_uploads_only = public_uploads_only
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name="shiftos-web-worker")

    def _run(self):
        while not self.stop.is_set():
            try:
                if self.public_uploads_only:
                    run_once(
                        self.database,
                        self.settings,
                        allowed_kinds=public_uploads.PUBLIC_JOB_KINDS,
                        institution_ids=public_uploads.active_session_institutions(self.database),
                        offline_analysis_only=True,
                    )
                else:
                    run_once(self.database, self.settings)
            except Exception:
                logger.error("web_worker_iteration_failed")
            self.stop.wait(2)

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=60)
        if self.thread.is_alive():
            raise RuntimeError("The worker has not completed shutdown")


def create_web_app(settings=None, database: Database | None = None, options=None):
    settings = settings or deployment_settings()
    options = options or WebOptions.from_env()
    if settings.api_access_mode != "scoped":
        raise ValueError("The web launcher requires explicit scoped API access")
    validate_access_configuration(settings)
    if settings.analysis_external_processing_allowed or settings.research_enabled:
        raise ValueError(
            "This demonstration launcher requires paid processing and research disabled"
        )
    if settings.gemini_enabled or settings.analysis_gemini_fallback_enabled:
        raise ValueError("Gemini must remain disabled in this web launcher")
    if options.public_uploads_enabled and not options.public_enabled:
        raise ValueError("Judge uploads require the explicitly enabled public demonstration")
    upload_secret = public_uploads.session_secret() if options.public_uploads_enabled else None
    dist = options.dist.resolve()
    if (
        not dist.is_dir()
        or not (dist / "index.html").is_file()
        or (dist / "index.html").is_symlink()
    ):
        raise ValueError("Build the frontend before starting the web launcher")
    if options.schema and not SCHEMA.fullmatch(options.schema):
        raise ValueError("Select an explicit valid PostgreSQL schema identifier")
    owns_database = database is None
    if database is None:
        url = make_url(settings.database_url.get_secret_value())
        if url.drivername != "postgresql+psycopg":
            raise ValueError("The deployed web launcher requires PostgreSQL")
        if options.schema:
            if "options" in url.query:
                raise ValueError("Do not combine a schema selection with database options")
            url = url.update_query_dict({"options": f"-csearch_path={options.schema}"})
        database = create_database(url.render_as_string(hide_password=False))
    # main.py retains a conventional module-level API app. Bootstrap its policy
    # path for that first import only, after the secret JSON has been validated
    # and materialised. Never alter a persisted environment/configuration file.
    previous_policy = os.environ.get("API_ACCESS_POLICY_PATH")
    os.environ["API_ACCESS_POLICY_PATH"] = str(settings.api_access_policy_path)
    try:
        from shiftos.main import create_app, error_response
    finally:
        if previous_policy is None:
            os.environ.pop("API_ACCESS_POLICY_PATH", None)
        else:
            os.environ["API_ACCESS_POLICY_PATH"] = previous_policy
    application = create_app(settings, database)
    # The deployment-facing OpenAPI title changes only in this wrapper; the
    # existing backend factory and exported frontend contracts stay unchanged.
    application.title = "NORDYC"
    prior_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        worker = None
        try:
            with database.engine.connect() as connection:
                if connection.dialect.name == "postgresql" and options.schema:
                    if connection.scalar(text("SELECT current_schema()")) != options.schema:
                        raise ValueError("The selected PostgreSQL schema is unavailable")
                heads = list(
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
                )
                if heads != ["0007_academic_action_plans"]:
                    raise ValueError("Apply the documented migrations before web startup")
            if options.public_enabled:
                _public_principal(settings, database, options)
            if options.worker_enabled or options.public_uploads_enabled:
                worker = WebWorker(
                    database, settings, public_uploads_only=options.public_uploads_enabled
                )
                worker.start()
            async with prior_lifespan(app):
                yield
        finally:
            if worker:
                worker.close()
            if owns_database:
                database.engine.dispose()
            policy_path = settings.api_access_policy_path
            if policy_path in MATERIALISED_POLICIES:
                policy_path.unlink(missing_ok=True)
                policy_path.parent.rmdir()
                MATERIALISED_POLICIES.discard(policy_path)

    application.router.lifespan_context = lifespan

    @application.middleware("http")
    async def public_boundary(request: Request, call_next):
        anonymous = "authorization" not in request.headers
        upload_session = None
        if upload_secret and anonymous and request.url.path.startswith("/api/v1/"):
            upload_session = await run_in_threadpool(
                public_uploads.resolve_session,
                database,
                request.cookies.get(public_uploads.COOKIE),
                upload_secret,
            )
        if upload_session:
            try:
                await run_in_threadpool(_public_principal, settings, database, options)
            except Exception:
                return error_response(
                    "DEMO_UNAVAILABLE", "The public demonstration is unavailable", 503
                )
            if request.method not in {"GET", "HEAD"}:
                if request.method != "POST" or not public_uploads.same_origin(request):
                    return error_response("FORBIDDEN", "This judge action is unavailable", 403)
                try:
                    if request.url.path.endswith("/curriculum-pdf"):
                        if request.query_params:
                            raise DomainError(
                                "FORBIDDEN", "Judge upload options are not supported", 403
                            )
                        payload = None
                    else:
                        if int(request.headers.get("content-length", "0")) > 8192:
                            raise DomainError(
                                "PAYLOAD_TOO_LARGE", "The judge request is too large", 413
                            )
                        raw = await request.body()
                        if len(raw) > 8192:
                            raise DomainError(
                                "PAYLOAD_TOO_LARGE", "The judge request is too large", 413
                            )
                        payload = json.loads(raw)
                    await run_in_threadpool(
                        public_uploads.reserve_submission,
                        database,
                        upload_session,
                        request.url.path,
                        payload,
                    )
                except DomainError as failure:
                    return error_response(failure.code, failure.message, failure.status_code)
                except (TypeError, ValueError):
                    return error_response(
                        "VALIDATION_ERROR", "Supply a valid bounded judge request", 422
                    )
            request.state.access_principal = public_uploads.principal_for(
                upload_session,
                options.public_institution_id,
                mutation=request.method not in {"GET", "HEAD"},
            )
        if (
            options.public_enabled
            and request.method in {"GET", "HEAD"}
            and request.url.path.startswith("/api/v1/")
            and anonymous
            and not upload_session
        ):
            try:
                request.state.access_principal = await run_in_threadpool(
                    _public_principal, settings, database, options
                )
            except Exception:
                unavailable = error_response(
                    "DEMO_UNAVAILABLE", "The public demonstration is unavailable", 503
                )
                unavailable.headers["Cache-Control"] = "no-store"
                unavailable.headers["X-Content-Type-Options"] = "nosniff"
                return unavailable
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # AJV compiles only the application's bundled, trusted OpenAPI schemas
        # using Function. This new deployment header must permit that existing
        # runtime compiler; external and inline scripts remain prohibited.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @application.get("/__public_demo", include_in_schema=False)
    def public_marker(request: Request):
        enabled = options.public_enabled
        if enabled:
            try:
                _public_principal(settings, database, options)
            except Exception:
                enabled = False
        value = {"enabled": enabled}
        if options.public_uploads_enabled:
            value["uploads_enabled"] = bool(enabled and upload_secret)
            upload_session = (
                public_uploads.resolve_session(
                    database, request.cookies.get(public_uploads.COOKIE), upload_secret
                )
                if upload_secret
                else None
            )
            if upload_session:
                value["upload_institution_id"] = str(upload_session["institution_id"])
        return JSONResponse(value, headers={"Cache-Control": "no-store"})

    @application.post("/__public_upload_session", include_in_schema=False)
    async def public_upload_session(request: Request):
        if not upload_secret or not options.public_uploads_enabled:
            return error_response("NOT_FOUND", "The requested resource was not found", 404)
        if not public_uploads.same_origin(request) or "authorization" in request.headers:
            return error_response("FORBIDDEN", "This judge action is unavailable", 403)
        try:
            if int(request.headers.get("content-length", "0")) > 8192:
                raise ValueError
            raw = await request.body()
            if len(raw) > 8192:
                raise ValueError
            value = public_uploads.PublicUploadRequest.model_validate_json(raw)
        except ValueError:
            return error_response(
                "VALIDATION_ERROR", "Supply the programme and official origin details", 422
            )
        existing = await run_in_threadpool(
            public_uploads.resolve_session,
            database,
            request.cookies.get(public_uploads.COOKIE),
            upload_secret,
        )
        if existing:
            return JSONResponse(
                {
                    "programme_id": str(existing["programme_id"]),
                    "institution_id": str(existing["institution_id"]),
                    "expires_in_seconds": max(0, existing["expires_at"] - int(time())),
                },
                headers={"Cache-Control": "no-store"},
            )
        try:
            value, cookie = await run_in_threadpool(
                public_uploads.create_session,
                database,
                value,
                upload_secret,
                request.client.host if request.client else "unknown",
            )
        except DomainError as failure:
            return error_response(failure.code, failure.message, failure.status_code)
        response = JSONResponse(value, status_code=201, headers={"Cache-Control": "no-store"})
        response.set_cookie(
            public_uploads.COOKIE,
            cookie,
            max_age=public_uploads.SESSION_SECONDS,
            httponly=True,
            secure=settings.app_env == "production",
            samesite="strict",
            path="/",
        )
        return response

    @application.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(path: str):
        if (
            path.startswith(("api/", "health", "__"))
            or path == "api"
            or any(part in {".", ".."} or part.startswith(".") for part in path.split("/"))
            or "\\" in path
            or "%" in path
        ):
            return error_response("NOT_FOUND", "The requested resource was not found", 404)
        asset = dist / path
        if path.startswith("assets/") or path in {"favicon.svg", "favicon.ico"}:
            if (
                asset.suffix.lower() not in ASSET_TYPES
                or ".private." in asset.name
                or any(part.startswith(".") for part in asset.relative_to(dist).parts)
                or not asset.resolve().is_relative_to(dist)
                or any(
                    parent.is_symlink()
                    for parent in [asset, *asset.parents]
                    if parent != dist.parent
                )
                or not asset.is_file()
            ):
                return error_response("NOT_FOUND", "The requested resource was not found", 404)
            cache = (
                "public, max-age=31536000, immutable"
                if HASHED_ASSET.fullmatch(asset.name)
                else "no-cache"
            )
            return FileResponse(asset, headers={"Cache-Control": cache})
        if SPA.fullmatch(path):
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-store"})
        return error_response("NOT_FOUND", "The requested resource was not found", 404)

    # Bound bytes/deadlines before the session middleware reads JSON. The
    # existing API body limiter remains intact; PDF requests retain its 20 MB cap.
    application.add_middleware(BodyLimitMiddleware)
    return application
