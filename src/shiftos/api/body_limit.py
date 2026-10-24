"""Bound request bytes before FastAPI JSON decoding, including chunked input."""

import asyncio
import re
from uuid import uuid4

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = 1_048_576, read_timeout_seconds: float = 30):
        self.app, self.max_bytes = app, max_bytes
        self.read_timeout_seconds = read_timeout_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        chunks, total = [], 0
        limit = self.max_bytes
        if re.fullmatch(
            r"/api/v1/programmes/[0-9a-fA-F-]{36}/curriculum-pdf", scope.get("path", "")
        ):
            limit = 20_000_000
        deadline = asyncio.get_running_loop().time() + self.read_timeout_seconds
        while True:
            try:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except TimeoutError:
                await JSONResponse(
                    status_code=408,
                    content={
                        "error": {
                            "code": "REQUEST_TIMEOUT",
                            "message": "Request body timed out",
                            "details": [],
                        }
                    },
                    headers={"X-Request-ID": str(uuid4())},
                )(scope, receive, send)
                return
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > limit:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "Request exceeds the permitted upload size"
                            if limit != self.max_bytes
                            else "Request exceeds the 1 MiB catalogue limit",
                            "details": [],
                        }
                    },
                    headers={"X-Request-ID": str(uuid4())},
                )
                await response(scope, receive, send)
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
