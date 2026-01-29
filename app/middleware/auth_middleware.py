"""
Authentication middleware: validates either JWT (Authorization) or API key + user_id.
- If Authorization Bearer token is present and valid -> set request.state.user and proceed.
- If no/invalid Authorization -> check for apiKey in headers; if present, validate against
  Company table, then require user_id from body (or query for GET) and set request.state.user.
- Exempt paths (/, /auth, /docs, /openapi.json, /redoc, /companies/create) skip auth.
"""

import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.database import SessionLocal
from app.models.user_model import User
from app.models.company_model import Company
from app.utils.jwt_utils import decode_access_token

logger = logging.getLogger(__name__)

# Paths that do not require authentication
AUTH_EXEMPT_PREFIXES = ("/auth",)
AUTH_EXEMPT_EXACT = {"/", "/docs", "/openapi.json", "/redoc", "/companies/create", "/subscriptions","/subscriptions/callback"}

# Header names for API key (case-insensitive via .get which normalizes)
APIKEY_HEADERS = ("x-api-key", "apikey")


def _is_exempt(path: str) -> bool:
    if path in AUTH_EXEMPT_EXACT:
        return True
    if any(path.startswith(p) for p in AUTH_EXEMPT_PREFIXES):
        return True
    return False


def _get_apikey(request: Request) -> str | None:
    for h in APIKEY_HEADERS:
        v = request.headers.get(h)
        if v and v.strip():
            return v.strip()
    return None


def _get_user_id_from_body_or_query(request: Request, body_bytes: bytes) -> str | None:
    # Prefer body (JSON) for POST/PUT/PATCH
    if body_bytes and body_bytes.strip():
        try:
            data = json.loads(body_bytes)
            if isinstance(data, dict) and data.get("user_id"):
                return str(data["user_id"]).strip()
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: query (e.g. for GET)
    return request.query_params.get("user_id") or None


async def _replay_body(request: Request, body: bytes) -> None:
    """Make the body available again for the route handler after it was consumed."""

    async def _receive():
        return {"type": "http.request", "body": body}

    request._receive = _receive


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if _is_exempt(path):
            return await call_next(request)

        db = SessionLocal()
        try:
            # 1) Try Authorization Bearer (JWT)
            auth = request.headers.get("authorization")
            if auth and auth.startswith("Bearer "):
                token = auth[7:].strip()
                if token:
                    try:
                        payload = decode_access_token(token)
                        user_id = payload.get("user_id")
                        if user_id:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user and user.is_active:
                                request.state.user = user
                                return await call_next(request)
                    except Exception:
                        pass
                    # Invalid/expired JWT -> do not fall through to apiKey; require valid auth
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Could not validate credentials"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # 2) No valid JWT -> try API key in headers
            apikey = _get_apikey(request)
            if not apikey:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing authorization: provide Authorization Bearer or apiKey header"},
                )

            company = db.query(Company).filter(Company.apikey == apikey).first()
            if not company:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key. Access denied."},
                )

            # 3) API key valid -> require user_id from body or query
            body = await request.body()
            user_id = _get_user_id_from_body_or_query(request, body)
            if not user_id:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "When using apiKey, user_id is required in request body or query (user_id=...)."},
                )

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "User not found for the given user_id."},
                )
            if not user.is_active:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "User account is inactive."},
                )

            # Replay body so the route can read it
            await _replay_body(request, body)
            request.state.user = user
            return await call_next(request)

        finally:
            db.close()
