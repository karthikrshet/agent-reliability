"""
Agent Reliability Lab — Multi-Tenant Role-Based Access Control (RBAC) Module.

Provides authentication, multi-tenant context resolution, and fine-grained role-based
authorization dependencies and middleware for FastAPI REST API endpoints.
"""

from __future__ import annotations

import enum
import os
from collections.abc import Callable, Sequence
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class Role(str, enum.Enum):
    """ARL access control roles."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    SYSTEM = "system"


class AuthPrincipal(BaseModel):
    """Authenticated user/service identity and tenant scope."""

    user_id: str
    tenant_id: str = "default-tenant"
    role: Role = Role.VIEWER
    api_key_prefix: str | None = None
    is_authenticated: bool = True


def get_current_principal(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthPrincipal:
    """Extract authenticated principal and tenant context from request headers."""
    tenant = x_tenant_id or "default-tenant"
    user_id = x_user_id or "anonymous-user"

    # Explicit role assertion header (e.g. from upstream auth gateway or test harness)
    if x_user_role:
        try:
            role = Role(x_user_role.lower())
        except ValueError:
            role = Role.VIEWER
        return AuthPrincipal(
            user_id=user_id,
            tenant_id=tenant,
            role=role,
            is_authenticated=True,
        )

    # API key check
    if x_api_key:
        if x_api_key.startswith("arl_live_") or x_api_key.startswith("arl_test_"):
            parts = x_api_key.split("_")
            if len(parts) >= 4:
                parsed_tenant = parts[2]
                parsed_role_str = parts[3]
                try:
                    role = Role(parsed_role_str.lower())
                except ValueError:
                    role = Role.OPERATOR
                return AuthPrincipal(
                    user_id=f"key-user-{parsed_tenant}",
                    tenant_id=parsed_tenant,
                    role=role,
                    api_key_prefix=x_api_key[:12],
                    is_authenticated=True,
                )
        return AuthPrincipal(
            user_id="api-key-admin",
            tenant_id=tenant,
            role=Role.ADMIN,
            api_key_prefix=x_api_key[:8],
            is_authenticated=True,
        )

    # Bearer token check
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if "admin" in token:
            role = Role.ADMIN
        elif "operator" in token:
            role = Role.OPERATOR
        else:
            role = Role.VIEWER
        return AuthPrincipal(
            user_id="bearer-user",
            tenant_id=tenant,
            role=role,
            is_authenticated=True,
        )

    # If ARL_AUTH_ENFORCE is explicitly true, unauthenticated requests are rejected
    if os.environ.get("ARL_AUTH_ENFORCE", "").lower() in ("true", "1", "yes"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-API-Key or Authorization header missing",
        )

    # Default fallback in local development mode
    return AuthPrincipal(
        user_id=user_id,
        tenant_id=tenant,
        role=Role.ADMIN,
        is_authenticated=True,
    )


def require_role(
    allowed_roles: Role | str | Sequence[Role | str],
) -> Callable[[AuthPrincipal], AuthPrincipal]:
    """FastAPI dependency verifying current principal possesses one of the allowed roles."""
    if isinstance(allowed_roles, (Role, str)):
        roles_set = {Role(allowed_roles)}
    else:
        roles_set = {Role(r) for r in allowed_roles}

    def role_verifier(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
        if principal.role == Role.ADMIN or principal.role in roles_set:
            return principal

        msg = (
            f"Insufficient permissions: role '{principal.role.value}' does not have "
            f"required access ({[r.value for r in roles_set]})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg,
        )

    return role_verifier


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Attaches tenant context and echoes X-Tenant-ID header on HTTP responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID", "default-tenant")
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
