"""Export the public OpenAPI contract without connecting to a database or provider."""

import json
from pathlib import Path

from shiftos.core.config import Settings
from shiftos.main import create_app


def main():
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        Settings(
            _env_file=None,
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            analysis_external_processing_allowed=False,
            research_enabled=False,
            analysis_gemini_fallback_enabled=False,
        )
    )
    contract = app.openapi()
    # Python 3.12/3.13 name HTTP 422 differently. Canonicalise only the default
    # documentation label; preserve every response schema and custom description.
    for path_item in contract.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            response = operation.get("responses", {}).get("422")
            if isinstance(response, dict) and response.get("description") in {
                "Unprocessable Entity",
                "Unprocessable Content",
            }:
                response["description"] = "Unprocessable Content"
    path = root / "frontend/src/api/openapi.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    app.state.database.engine.dispose()
    print("Public OpenAPI contract exported; no database or provider request executed.")


if __name__ == "__main__":
    main()
