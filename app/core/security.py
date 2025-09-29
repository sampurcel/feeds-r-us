from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Set

from fastapi import Depends, Header, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select

from app.db.session import get_db
from app.models import UserProfile, UserRole
from app.services.auth import TokenValidationError, extract_roles, validate_jwt


@dataclass
class AuthContext:
    user: UserProfile
    claims: dict[str, Any]
    token_roles: Set[str]


async def get_token_claims(authorization: str | None) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
    scheme, param = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not param:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    try:
        return await validate_jwt(param)
    except TokenValidationError as exc:  # pragma: no cover - runtime path
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db=Depends(get_db),
) -> AuthContext:
    claims = await get_token_claims(authorization)
    token_roles = extract_roles(claims)
    object_id = claims.get("oid") or claims.get("sub")
    if not object_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing object id")

    result = await db.execute(select(UserProfile).where(UserProfile.user_object_id == object_id))
    user = result.scalars().first()
    if user is None:
        user = UserProfile(
            user_object_id=object_id,
            email=claims.get("preferred_username") or claims.get("upn") or claims.get("email", ""),
            display_name=claims.get("name"),
            role=UserRole.ANALYST,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return AuthContext(user=user, claims=claims, token_roles=token_roles)


def require_roles(*roles: UserRole):
    async def dependency(context: AuthContext = Depends(get_current_user)) -> AuthContext:
        effective_roles = set(context.token_roles)
        user_role = context.user.role.value if isinstance(context.user.role, UserRole) else context.user.role
        effective_roles.add(user_role)
        if roles and not any(role.value in effective_roles for role in roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return context

    return dependency
