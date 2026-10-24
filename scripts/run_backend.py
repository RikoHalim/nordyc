"""Start only the API; worker and migrations remain explicit administrative commands."""

import os

import uvicorn

from shiftos.core.access import validate_access_configuration
from shiftos.core.config import Settings
from shiftos.core.errors import DomainError


def main():
    try:
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("Configure PORT as an integer from 1 to 65535") from None
    settings = Settings()
    try:
        if settings.api_access_mode != "scoped":
            raise ValueError
        validate_access_configuration(settings)
    except (DomainError, ValueError):
        raise SystemExit("The network API launcher requires a valid scoped access policy") from None
    uvicorn.run("shiftos.main:app", host="0.0.0.0", port=port, access_log=False)


if __name__ == "__main__":
    main()
