"""
Agent Reliability Lab — FastAPI Server Package.
"""

from __future__ import annotations

from arl.server.auth import (
    AuthPrincipal,
    Role,
    TenantContextMiddleware,
    get_current_principal,
    require_role,
)
from arl.server.main import app, create_app

__all__ = [
    "AuthPrincipal",
    "Role",
    "TenantContextMiddleware",
    "app",
    "create_app",
    "get_current_principal",
    "require_role",
]
