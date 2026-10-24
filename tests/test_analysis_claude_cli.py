"""Offline CLI checks; synthetic settings and no external provider or database."""

import json
from pathlib import Path

import pytest

from shiftos import cli
from shiftos.core.config import Settings
from shiftos.services.analysis import claude_verification


@pytest.fixture
def isolated_settings(monkeypatch):
    settings = Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(cli, "Settings", lambda: settings)

    def forbidden(*args, **kwargs):
        raise AssertionError("Provider verification must not construct a database")

    monkeypatch.setattr(cli, "create_database", forbidden)
    return settings


def test_cli_preflight_reports_actual_missing_configuration_without_live_call(
    monkeypatch, isolated_settings, tmp_path, capsys
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preflight cannot call the live helper")

    monkeypatch.setattr(claude_verification, "verify_claude", forbidden)
    report_path = tmp_path / "synthetic-preflight-report.json"
    assert cli.main(["verify-claude", "--report", str(report_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert report["provider_requests"] == 0
    assert "managed_credential_missing" in report["blockers"]
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_cli_live_flag_explicitly_selects_bounded_helper(monkeypatch, isolated_settings, capsys):
    calls = []

    def synthetic_check(settings):
        calls.append(settings)
        return {"status": "failed", "is_synthetic": True, "provider_requests": 0}

    monkeypatch.setattr(claude_verification, "verify_claude", synthetic_check)
    assert cli.main(["verify-claude", "--live"]) == 1
    assert calls == [isolated_settings]
    assert json.loads(capsys.readouterr().out)["is_synthetic"] is True


def test_cli_configuration_errors_are_structured_and_secret_free(
    monkeypatch, isolated_settings, capsys
):
    def invalid_configuration():
        raise ValueError("SYNTHETIC-private-configuration-must-not-be-printed")

    monkeypatch.setattr(cli, "Settings", invalid_configuration)
    assert cli.main(["verify-claude"]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC-private" not in output
    assert json.loads(output) == {
        "status": "blocked",
        "provider": "replit_claude",
        "provider_requests": 0,
        "error_code": "verification_configuration_or_report_invalid",
    }


@pytest.mark.parametrize("operation", ["mkdir", "write_text"])
def test_cli_report_export_failure_preserves_actual_activity_and_usage(
    monkeypatch, isolated_settings, tmp_path, capsys, operation
):
    synthetic_report = {
        "status": "live_verified",
        "is_synthetic": True,
        "actual_model": "claude-opus-5",
        "provider_requests": 1,
        "usage": {"input_tokens": 17, "output_tokens": 13},
        "observed_cost": None,
    }
    monkeypatch.setattr(
        claude_verification, "verify_claude", lambda settings: synthetic_report.copy()
    )

    def denied(*args, **kwargs):
        raise PermissionError("SYNTHETIC-private-path-must-not-be-printed")

    monkeypatch.setattr(Path, operation, denied)
    assert cli.main(["verify-claude", "--live", "--report", str(tmp_path / "report.json")]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC-private" not in output
    report = json.loads(output)
    assert {key: report[key] for key in synthetic_report} == synthetic_report
    assert report["report_write_failed"] is True
    assert report["report_error_code"] == "verification_report_write_failed"
