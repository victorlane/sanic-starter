"""Protected routes: demonstrate ``@protected`` and ``@require_scopes``.

- ``GET /me``       — any authenticated caller (valid JWT).
- ``GET /me/admin`` — authenticated AND carrying the ``admin`` scope.

``@protected`` puts the decoded JWT claims on ``request.ctx.user``.
``@openapi.secured("token")`` marks the endpoint as needing bearer auth in
the generated spec.
"""

from __future__ import annotations

from sanic import Blueprint, Request, json
from sanic_ext import openapi

from app.security import protected, require_scopes


me = Blueprint("me", url_prefix="/me")


@me.get("/")
@openapi.tag("me")
@openapi.summary("Return the current authenticated user")
@openapi.secured("token")
@protected
async def whoami(request: Request):
    return json({"user": request.ctx.user})


@me.get("/admin")
@openapi.tag("me")
@openapi.summary("Admin-only endpoint (requires the 'admin' scope)")
@openapi.secured("token")
@protected
@require_scopes("admin")
async def admin_only(request: Request):
    return json({"ok": True, "user": request.ctx.user})
