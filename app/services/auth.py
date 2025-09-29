from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import httpx
from jose import jwk, jwt
from jose.utils import base64url_decode

from app.core.config import settings


class TokenValidationError(Exception):
    """Raised when JWT validation fails."""


@lru_cache(maxsize=1)
def _jwks_cache() -> dict[str, Any]:
    return {"keys": [], "cached_at": 0.0}


async def _refresh_jwks(force: bool = False) -> dict[str, Any]:
    cache = _jwks_cache()
    now = time.time()
    if force or now - cache["cached_at"] > settings.jwks_cache_ttl or not cache["keys"]:
        if not settings.tenant_id:
            raise TokenValidationError("Tenant ID is not configured")
        jwks_uri = (
            f"{settings.authority_host}/{settings.tenant_id}/discovery/v2.0/keys"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri, timeout=10)
            response.raise_for_status()
            jwks = response.json()
        cache["keys"] = jwks.get("keys", [])
        cache["cached_at"] = now
    return cache


async def validate_jwt(token: str) -> dict[str, Any]:
    """Validate a JWT against the configured Azure AD tenant."""

    header = jwt.get_unverified_header(token)
    jwks_cache = await _refresh_jwks()

    key = next((k for k in jwks_cache["keys"] if k["kid"] == header["kid"]), None)
    if not key:
        jwks_cache = await _refresh_jwks(force=True)
        key = next((k for k in jwks_cache["keys"] if k["kid"] == header["kid"]), None)
    if not key:
        raise TokenValidationError("Signing key not found")

    message, encoded_signature = token.rsplit(".", maxsplit=1)
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

    public_key = jwk.construct(key)
    if not public_key.verify(message.encode("utf-8"), decoded_signature):
        raise TokenValidationError("Invalid token signature")

    claims = jwt.get_unverified_claims(token)

    if settings.allowed_audiences and claims.get("aud") not in settings.allowed_audiences:
        raise TokenValidationError("Invalid audience")
    if settings.client_id and claims.get("aud") != settings.client_id:
        raise TokenValidationError("Token audience mismatch")
    if claims.get("iss") != f"{settings.authority_host}/{settings.tenant_id}/v2.0":
        raise TokenValidationError("Invalid issuer")

    if time.time() > float(claims.get("exp", 0)):
        raise TokenValidationError("Token expired")

    return claims


def extract_roles(claims: dict[str, Any]) -> set[str]:
    """Extract application roles from JWT claims."""

    roles: set[str] = set()
    if roles_claim := claims.get("roles"):
        roles.update(roles_claim if isinstance(roles_claim, list) else [roles_claim])
    if groups_claim := claims.get("groups"):
        roles.update(groups_claim if isinstance(groups_claim, list) else [groups_claim])
    if app_role := claims.get("app_role"):
        roles.add(str(app_role))
    return roles
