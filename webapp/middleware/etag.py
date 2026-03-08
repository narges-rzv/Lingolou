"""
ETag middleware for all GET responses.

Adds ETag headers and returns 304 Not Modified when the client sends
a matching If-None-Match header, saving bandwidth on unchanged responses.
Covers API JSON, index.html, and static assets.
"""

from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ETagMiddleware(BaseHTTPMiddleware):
    """Add ETag / 304 support for all GET 200 responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and add ETag if applicable."""
        if request.method != "GET":
            return await call_next(request)

        response = await call_next(request)

        if response.status_code != 200:
            return response

        # Read the streaming response body
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        # Compute ETag from body hash
        etag = f'"{hashlib.md5(body, usedforsecurity=False).hexdigest()}"'

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})

        # Return original response with ETag header added
        headers = dict(response.headers)
        headers.pop("etag", None)  # remove FileResponse's own ETag to avoid duplicates
        headers["ETag"] = etag
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
