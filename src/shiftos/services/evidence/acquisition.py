"""Reuse the catalogue's bounded transport, with a separate official-data policy."""

import hashlib
from dataclasses import dataclass
from datetime import datetime

from shiftos.db.base import utc_now
from shiftos.services.ingestion.fetcher import FetchError, SafeFetcher


@dataclass(frozen=True)
class Artifact:
    url: str
    content: bytes
    sha256: str
    retrieved_at: datetime


class DatasetFetcher(SafeFetcher):
    reviewed_hosts = frozenset(
        {
            "www.dosm.gov.my",
            "storage.dosm.gov.my",
            "ec.europa.eu",
            "unstats.un.org",
            "www.ilo.org",
            "www2.mqa.gov.my",
        }
    )
    accepted_suffixes = frozenset({".csv", ".xlsx", ".json", ".pdf", ".php"})
    accepted_types = frozenset(
        {
            "text/csv",
            "application/csv",
            "application/json",
            "application/pdf",
            "application/octet-stream",
            "binary/octet-stream",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
    )

    def fetch(self, url: str) -> Artifact:
        if not self.enabled or not self.terms_reviewed:
            raise FetchError("live_fetch_disabled", "Enable acquisition after source terms review.")
        final_url, content, _ = self._request(url, robots=False)
        if not content or content.lstrip().lower().startswith((b"<!doctype", b"<html")):
            raise FetchError(
                "invalid_artifact", "Empty data or HTML landing/challenge page returned."
            )
        return Artifact(final_url, content, hashlib.sha256(content).hexdigest(), utc_now())
