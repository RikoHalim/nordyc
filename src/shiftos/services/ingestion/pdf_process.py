"""Bound untrusted PDF CPU/wall time outside the database worker process.

This is a resource boundary, not a general operating-system security sandbox.
No provider secrets, application environment or network tools are passed to it.
"""

import base64
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from shiftos.schemas.ingestion import CatalogueImport
from shiftos.services.ingestion.parsers import CurriculumParseError


def prepare_in_process(content, *, regions, metadata, timeout_seconds=30):
    package_source = Path(__file__).resolve().parents[3]
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    environment.update(PYTHONPATH=str(package_source), PYTHONIOENCODING="utf-8")
    payload = {
        "content": base64.b64encode(content).decode("ascii"),
        "regions": regions,
        "metadata": metadata,
    }
    try:
        result = subprocess.run(
            [sys.executable, "-m", "shiftos.services.ingestion.pdf_process"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
            timeout=timeout_seconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        if result.returncode or len(result.stdout) > 2_000_000:
            raise ValueError
        response = json.loads(result.stdout)
        if response.get("error"):
            code = response["error"]
            if not isinstance(code, str) or not code.startswith("pdf_") or len(code) > 80:
                code = "pdf_extraction_failed"
            raise CurriculumParseError(code, "PDF candidate extraction failed; use reviewed JSON")
        return CatalogueImport.model_validate(response["data"]), response["regions"]
    except subprocess.TimeoutExpired:
        raise CurriculumParseError(
            "pdf_processing_timeout", "PDF processing deadline exceeded; use reviewed JSON"
        ) from None
    except CurriculumParseError:
        raise
    except (ValueError, KeyError, TypeError, OSError):
        raise CurriculumParseError(
            "pdf_processing_failed", "PDF processing failed; use reviewed JSON"
        ) from None


def _child():
    logging.disable(logging.CRITICAL)
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    from shiftos.services.ingestion.pdf import (
        PdfCourseRegion,
        detect_brochure_regions,
        prepare_brochure_import,
    )

    try:
        raw = sys.stdin.buffer.read(28_000_001)
        if len(raw) > 28_000_000:
            raise ValueError
        payload = json.loads(raw)
        content = base64.b64decode(payload["content"], validate=True)
        regions = (
            [PdfCourseRegion.model_validate(row) for row in payload["regions"]]
            if payload.get("regions")
            else detect_brochure_regions(content)
        )
        metadata = payload["metadata"]
        metadata["retrieved_at"] = datetime.fromisoformat(metadata["retrieved_at"])
        data = prepare_brochure_import(content, regions=regions, **metadata)
        output = {
            "data": data.model_dump(mode="json"),
            "regions": [row.model_dump(mode="json") for row in regions],
        }
        encoded = json.dumps(output).encode("utf-8")
        if len(encoded) > 2_000_000:
            raise ValueError
        sys.stdout.buffer.write(encoded)
    except CurriculumParseError as exc:
        print(json.dumps({"error": exc.code}))
    except Exception:
        print(json.dumps({"error": "pdf_extraction_failed"}))


if __name__ == "__main__":
    _child()
