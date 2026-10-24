"""Validate the research catalogue without promoting access research into ingestion success."""

import csv
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shiftos.core.enums import EvidenceClass

REGISTRY_COLUMNS = (
    "id category priority name publisher source_url download_api_url "
    "resource_type format geography "
    "discipline_occupation_coverage available_years latest_verified_publication_date "
    "observation_period publisher_update_frequency licence licence_url rights_status "
    "registration_payment verified_fields evidence_class evidence_subtype relevance limitations "
    "recommended_ingestion verification_status endpoint_verification verified_on data_quality "
    "integration_ease reliability reusability maintenance course_relevance_support "
    "robots_automation_status acquired_into_backend"
).split()


def validate_public_url(value: str) -> str:
    """Syntax only: acquisition separately checks DNS, hosts, redirects and robots."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Expected an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Credentials and fragments are not permitted in dataset URLs")
    return value


class RegistryEntry(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z0-9-]+$")
    category: Literal["A", "B", "C", "D", "E", "F"]
    priority: Literal["P0", "P1", "P2"]
    name: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    source_url: str
    download_api_url: str = ""
    format: str
    evidence_class: EvidenceClass
    verification_status: Literal["Verified", "Partially verified", "Unverified"]
    verified_on: date
    latest_verified_publication_date: str = "Unknown"
    licence: str = "Unknown"
    licence_url: str = ""
    rights_status: str = "Unknown"
    limitations: str = ""
    acquired_into_backend: Literal["No", "Yes", "Partial"] = "No"

    @field_validator("source_url")
    @classmethod
    def source_is_url(cls, value: str) -> str:
        return validate_public_url(value)

    @field_validator("download_api_url", "licence_url")
    @classmethod
    def optional_url(cls, value: str) -> str:
        if value:
            validate_public_url(value)
        return value

    @property
    def download_urls(self) -> list[str]:
        # Do not silently fall back to source_url: most of those are landing pages.
        return [self.download_api_url] if self.download_api_url else []

    @property
    def publication_date(self) -> date | None:
        # Date prose/year precision remains available verbatim in the registry metadata.
        value = self.latest_verified_publication_date
        return date.fromisoformat(value) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def read_registry(path: Path | str) -> list[RegistryEntry]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(REGISTRY_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Registry missing columns: {', '.join(sorted(missing))}")
        records = []
        seen = set()
        for number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Registry row {number}: excess columns")
            entry = RegistryEntry.model_validate(row)
            if entry.id in seen:
                raise ValueError(f"Registry row {number}: duplicate dataset ID {entry.id}")
            seen.add(entry.id)
            records.append(entry)
        if not records:
            raise ValueError("Registry contains no datasets")
        return records
