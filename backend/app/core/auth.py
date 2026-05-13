"""Simple API key authentication and role authorization helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


_ROLE_RANK: dict[str, int] = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    status_code: int = 200
    detail: str = "ok"
    role: str = "viewer"


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _load_api_keys(raw: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        key, role = chunk.split(":", 1)
        key = key.strip()
        role = role.strip().lower()
        if not key or role not in _ROLE_RANK:
            continue
        entries[key] = role
    return entries


def _extract_api_key(headers: Mapping[str, str]) -> str | None:
    auth_header = headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    x_api_key = headers.get("x-api-key", "").strip()
    if x_api_key:
        return x_api_key
    return None


def _required_role_for(method: str, path: str) -> str | None:
    if not path.startswith("/api"):
        return None
    if path.startswith("/api/health"):
        return None
    if path.startswith("/api/prop-network"):
        return None

    admin_prefixes = (
        "/api/update-center",
        "/api/system-settings",
        "/api/custom-admin",
    )
    if path.startswith(admin_prefixes):
        return "admin"

    upper = method.upper()
    if upper in {"GET", "HEAD", "OPTIONS"}:
        return "viewer"
    return "operator"


def authorize_request(method: str, path: str, headers: Mapping[str, str]) -> AuthDecision:
    """Authorize a request based on API key role mapping from environment."""
    auth_enabled = _is_truthy(os.getenv("AOJ_AUTH_ENABLED", "false"))
    required_role = _required_role_for(method, path)

    if required_role is None or not auth_enabled:
        return AuthDecision(allowed=True, role="viewer")

    raw_keys = os.getenv("AOJ_API_KEYS", "")
    api_keys = _load_api_keys(raw_keys)
    if not api_keys:
        return AuthDecision(
            allowed=False,
            status_code=503,
            detail="Authentication is enabled but AOJ_API_KEYS is not configured.",
            role="viewer",
        )

    provided_key = _extract_api_key(headers)
    if not provided_key:
        return AuthDecision(
            allowed=False,
            status_code=401,
            detail="Missing API key. Use Authorization: Bearer <key> or X-API-Key header.",
            role="viewer",
        )

    role = api_keys.get(provided_key)
    if role is None:
        return AuthDecision(
            allowed=False,
            status_code=401,
            detail="Invalid API key.",
            role="viewer",
        )

    if _ROLE_RANK[role] < _ROLE_RANK[required_role]:
        return AuthDecision(
            allowed=False,
            status_code=403,
            detail=f"Insufficient role. Required role: {required_role}",
            role=role,
        )

    return AuthDecision(allowed=True, role=role)
