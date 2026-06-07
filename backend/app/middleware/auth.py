"""Authentication middleware — open by default, extensible for full auth later.

When ``DASHBOARD_API_KEY`` is unset the app stays open (current dev/trusted-LAN mode).
When set, clients must send ``X-API-Key`` on protected routes.

Future full auth (v1.6+): replace ``_validate_request`` with session/JWT checks while
keeping the same middleware entry point and public path list.
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

PUBLIC_PREFIXES = (
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._requires_auth(request.url.path):
            return await call_next(request)
        settings = get_settings()
        if not settings.dashboard_api_key:
            return await call_next(request)
        provided = request.headers.get("X-API-Key")
        if provided != settings.dashboard_api_key:
            return JSONResponse(
                status_code=401, content={"detail": "Invalid or missing API key"}
            )
        return await call_next(request)

    @staticmethod
    def _requires_auth(path: str) -> bool:
        if path == "/" or path.startswith("/assets/"):
            return False
        return not any(path == prefix or path.startswith(f"{prefix}/") for prefix in PUBLIC_PREFIXES)