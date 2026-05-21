"""
Aethera AI - Optional API authentication.

A lightweight bearer/API-key gate for the HTTP API. It is **disabled by
default** (`API_AUTH_ENABLED=false`) so existing local/dev deployments keep
working; enable it (and set `API_KEYS`) before exposing PHI endpoints.

The matching logic here is pure Python and unit-tested; `main.py` wires it as
an HTTP middleware. This is authentication only — per-user authorization
(scoping each user's records) is a separate, larger piece of work.
"""

import hmac
import os
from typing import Iterable, Optional, Set

# Paths reachable without a key even when auth is enabled.
PUBLIC_PATHS: Set[str] = {
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def is_auth_enabled() -> bool:
    return os.getenv("API_AUTH_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def allowed_keys() -> Set[str]:
    raw = os.getenv("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def _extract_bearer(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def check_api_key(auth_header: Optional[str], keys: Iterable[str]) -> bool:
    """Return True if the request carries a valid bearer key.

    Uses a constant-time compare against each configured key to avoid leaking
    key material via timing.
    """
    token = _extract_bearer(auth_header)
    if not token:
        return False
    return any(hmac.compare_digest(token, k) for k in keys)


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    # Allow static assets / docs subpaths.
    return path.startswith("/docs") or path.startswith("/redoc")


def request_authorized(path: str, method: str, auth_header: Optional[str]) -> bool:
    """Decide whether a request may proceed.

    Open when auth is disabled, for non-/api paths, public paths, and CORS
    preflight (OPTIONS). Otherwise require a valid key.
    """
    if not is_auth_enabled():
        return True
    if method.upper() == "OPTIONS":
        return True
    if not path.startswith("/api/"):
        return True
    if is_public_path(path):
        return True
    return check_api_key(auth_header, allowed_keys())
