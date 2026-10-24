"""One explicit same-origin web process; no automatic migration or seeding."""

import os

import uvicorn

from shiftos.web import create_web_app


def main():
    try:
        port = int(os.environ.get("PORT", "8080"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("Configure PORT as an integer from 1 to 65535") from None
    uvicorn.run(create_web_app(), host="0.0.0.0", port=port, access_log=False)


if __name__ == "__main__":
    main()
