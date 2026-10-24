"""Export the public OpenAPI contract without connecting to a database or provider."""

import json
from pathlib import Path

from shiftos.core.config import Settings
from shiftos.main import create_app

HTTP_REASON_ALIASES = {
    "413": ("Content Too Large", "Request Entity Too Large"),
    "414": ("URI Too Long", "Request-URI Too Long"),
    "416": ("Range Not Satisfiable", "Requested Range Not Satisfiable"),
    "422": ("Unprocessable Content", "Unprocessable Entity"),
}


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
    # CPython 3.13 renamed four standard reason phrases. Canonicalise only these
    # known default labels; preserve all response schemas and custom descriptions.
    for path_item in contract.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for code, aliases in HTTP_REASON_ALIASES.items():
                response = operation.get("responses", {}).get(code)
                if isinstance(response, dict) and response.get("description") in aliases:
                    response["description"] = aliases[0]
    path = root / "frontend/src/api/openapi.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    app.state.database.engine.dispose()
    print("Public OpenAPI contract exported; no database or provider request executed.")


if __name__ == "__main__":
    main()
