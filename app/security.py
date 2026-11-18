"""Auth helpers built on the fork's ``sanic.contrib.auth`` primitives.

This module wires JWT auth into the framework's ``@protected`` / ``@scoped``
decorators. Handlers decorated with :data:`protected` get the decoded JWT
claims on ``request.ctx.user``; pair with :func:`require_scopes` for
authorization.
"""

from __future__ import annotations

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jwt.exceptions import PyJWTError
from sanic import Request
from sanic.contrib.auth import get_token, scoped
from sanic.contrib.auth import protected as _protected

# --- password hashing -------------------------------------------------------


# Argon2id with argon2-cffi's defaults (3 passes, 64 MiB, 4 lanes). Both
# helpers are CPU-bound and blocking: from a handler, call them through
# ``asyncio.to_thread`` so the event loop keeps serving other requests.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


# --- JWT --------------------------------------------------------------------


def issue_token(request: Request, claims: dict) -> str:
    # PyJWT >= 2.10 enforces RFC 7519: the "sub" claim must be a string.
    if "sub" in claims:
        claims = {**claims, "sub": str(claims["sub"])}
    return jwt.encode(claims, request.app.config.SECRET, algorithm="HS256")


def decode_token(request: Request) -> dict | None:
    """Return verified JWT claims from the request, or ``None``.

    Token is read via the framework's tri-source ``get_token`` (Authorization:
    Bearer header by default; extend with ``cookie=``/``query=`` if needed).
    """
    token = get_token(request, scheme="Bearer")
    if not token:
        return None
    try:
        return jwt.decode(
            token, request.app.config.SECRET, algorithms=["HS256"]
        )
    except PyJWTError:
        return None


async def _verify(request: Request) -> dict | None:
    return decode_token(request)


# ``@protected`` — 401s unauthenticated requests, puts claims on
# request.ctx.user
protected = _protected(_verify)


def require_scopes(*scopes: str):
    """``@require_scopes("admin")`` — 403s if the principal lacks a scope.

    Place *below* ``@protected`` so the principal is resolved first.
    """
    return scoped(
        list(scopes),
        get_scopes=lambda r: (getattr(r.ctx, "user", None) or {}).get(
            "scopes", []
        ),
    )
