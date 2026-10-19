
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


WINDOW_SECONDS = 60

# Exact paths only; existing GET routes are unaffected.
PATH_LIMITS = {
    "/api/auth/register": 5,
    "/api/auth/login": 10,
    "/api/companies": 10,
    "/api/recruiters": 10,
    "/api/jobs": 10,
    "/api/messages": 10,
    "/api/phone-numbers": 10,
    "/api/emails": 10,
    "/api/websites": 10,
    "/api/risk-assessments": 10,
}


class RequestRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-process request limits for selected POST endpoints."""

    def __init__(self, app, path_limits=None):
        super().__init__(app)
        self.path_limits = (
            PATH_LIMITS if path_limits is None else path_limits
        )
        self.requests = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next):
        limit = self.path_limits.get(request.url.path)

        if request.method != "POST" or limit is None:
            return await call_next(request)

        # Do not trust forwarded-IP headers unless a trusted proxy is configured.
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, request.url.path)
        now = monotonic()

        with self.lock:
            timestamps = self.requests[key]

            while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after = max(
                    1, int(WINDOW_SECONDS - (now - timestamps[0]))
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests. Please try again later."
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

        return await call_next(request)
