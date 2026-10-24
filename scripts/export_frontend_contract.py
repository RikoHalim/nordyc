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
    path = root / "frontend/src/api/openapi.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    app.state.database.engine.dispose()
    print("Public OpenAPI contract exported; no database or provider request executed.")


if __name__ == "__main__":
    main()
