"""Non-billable runtime inspection; no migration, acquisition or model invocation."""

import hashlib
import json
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from shiftos.core.errors import DomainError


def database_identity(settings):
    """Opaque same-process configuration receipt; never expose a DSN or credentials."""
    url = make_url(settings.database_url.get_secret_value())
    query = sorted(
        (key, list(value) if isinstance(value, tuple) else value)
        for key, value in url.query.items()
        if key.casefold() not in {"password", "sslpassword", "passfile"}
    )
    identity = (url.drivername, url.host, url.port, url.database, url.username, query)
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def migration_heads():
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    return sorted(ScriptDirectory.from_config(config).get_heads())


def runtime_report(settings, *, database=None, check_database=False, component="api"):
    checks, blockers = {}, []
    checks["python_supported"] = sys.version_info >= (3, 12)
    checks["postgresql_configured"] = (
        make_url(settings.database_url.get_secret_value()).drivername == "postgresql+psycopg"
    )
    checks["external_processing_disabled"] = not settings.analysis_external_processing_allowed
    checks["research_disabled"] = not settings.research_enabled
    checks["gemini_disabled"] = (
        not settings.gemini_enabled and not settings.analysis_gemini_fallback_enabled
    )
    checks["claude_selected"] = (
        settings.analysis_model_provider == "replit_claude"
        and settings.claude_model == "claude-opus-5"
    )
    checks["managed_credentials_present"] = bool(
        settings.replit_anthropic_api_key and settings.replit_anthropic_base_url
    )
    checks["brave_credential_present"] = bool(settings.brave_search_api_key)
    try:
        from shiftos.core.access import validate_access_configuration

        validate_access_configuration(settings)
        checks["access_configuration_valid"] = True
    except (DomainError, ValueError, OSError):
        checks["access_configuration_valid"] = False
    checks["scoped_authorization"] = getattr(settings, "api_access_mode", "legacy") == "scoped"
    source_policy = {"status": "invalid"}
    try:
        from shiftos.services.analysis.orchestrator import _permissions

        _, policy = _permissions(settings)
        checks["source_policy_valid"] = True
        source_policy = {"status": "valid", **policy}
    except DomainError:
        checks["source_policy_valid"] = False
    for name in (
        "python_supported",
        "postgresql_configured",
        "gemini_disabled",
        "claude_selected",
        "access_configuration_valid",
        "source_policy_valid",
    ):
        if not checks[name]:
            blockers.append(name)
    if settings.app_env == "production" and not checks["scoped_authorization"]:
        blockers.append("production_requires_scoped_access")
    upload = settings.curriculum_upload_dir
    checks["private_storage_configured"] = bool(str(upload))
    checks["private_storage_acl_verified"] = None
    if os.name != "nt" and upload.exists():
        checks["private_storage_acl_verified"] = not bool(upload.stat().st_mode & 0o077)
    heads = migration_heads()
    schema = {"status": "not_checked", "expected_heads": heads}
    if check_database:
        if database is None:
            blockers.append("explicit_database_connection_required")
        else:
            try:
                with database.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                    actual = sorted(
                        connection.execute(
                            text("SELECT version_num FROM alembic_version")
                        ).scalars()
                    )
                schema = {
                    "status": "current" if actual == heads else "migration_required",
                    "expected_heads": heads,
                    "actual_heads": actual,
                }
                if actual != heads:
                    blockers.append("migration_required")
            except SQLAlchemyError:
                schema["status"] = "database_or_schema_unavailable"
                blockers.append("database_or_schema_unavailable")
    return {
        "schema_version": "phase7-runtime-1",
        "component": component,
        "status": "blocked" if blockers else "configuration_checked",
        "environment": settings.app_env,
        "database_configuration_fingerprint": database_identity(settings),
        "checks": checks,
        "schema": schema,
        "source_policy": source_policy,
        "blockers": blockers,
        "provider_requests": 0,
        "migrations_executed": 0,
        "deployment_executed": False,
        "deployment_ready": False,
        "limitations": [
            "Configuration inspection is not operational deployment acceptance.",
            "Named identity, durable private storage, ACLs, process supervision and backups "
            "require deployment validation.",
            "Missing provider keys allow offline testing, not live-provider readiness.",
        ],
    }
