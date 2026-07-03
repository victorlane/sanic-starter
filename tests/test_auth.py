"""Smoke tests that exercise the wiring without a real Postgres.

The ``UserExecutor`` is dependency-injected, so tests override that dependency
with an in-memory fake — this is the payoff of DI: swap the data layer without
touching the routes.
"""

import os
import uuid

import pytest

from sanic import Sanic

os.environ.setdefault("APP_SECRET", "a-sufficiently-long-test-secret-key-32bytes")
os.environ.setdefault("SECURITY_HEADERS", "true")

from app.security import hash_password  # noqa: E402
from app.services.users import UserExecutor, UserRow  # noqa: E402


Sanic.test_mode = True


class FakeUsers(UserExecutor):
    """In-memory stand-in for the mayim executor."""

    def __init__(self):
        self._rows: dict[str, UserRow] = {}
        self._id = 0

    async def by_username(self, username: str):
        return self._rows.get(username)

    async def create(self, username, password_hash, scopes):
        self._id += 1
        row = UserRow(self._id, username, password_hash, scopes)
        self._rows[username] = row
        return row


@pytest.fixture
def app():
    from sanic_ext import Extend, Extension

    from app.server import create_app

    # Extensions register into process-global registries; clear BOTH so each
    # test builds a clean app. Extend.register() appends to Extend._pre_registry
    # (separate from Extension._name_registry), and the module-level
    # ``app = create_app()`` in app.server runs at import time with the mayim
    # extension — without this the real Postgres extension leaks into tests.
    Extension.reset()
    Extend._pre_registry.clear()

    application = create_app(f"test-{uuid.uuid4().hex}", use_db=False)
    # Replace the injected executor with the fake for the duration of the test.
    fake = FakeUsers()
    fake._rows["alice"] = UserRow(
        1, "alice", hash_password("pw"), ["user", "admin"]
    )
    # request_arg tells sanic-ext the constructor's request parameter name so
    # it injects the request into our factory (which just returns the fake).
    application.ext.add_dependency(
        UserExecutor, lambda request: fake, request_arg="request"
    )
    return application


def _token(app, scopes):
    """Mint a JWT for tests using the app's configured secret."""
    import jwt

    return jwt.encode(
        {"sub": "1", "username": "alice", "scopes": scopes},
        app.config.SECRET,
        algorithm="HS256",
    )


async def test_security_headers_present(app):
    _, resp = await app.asgi_client.post("/auth/login", json={})
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


async def test_login_returns_token(app):
    _, resp = await app.asgi_client.post(
        "/auth/login", json={"username": "alice", "password": "pw"}
    )
    assert resp.status == 200
    assert "token" in resp.json


async def test_protected_accepts_valid_token(app):
    token = _token(app, ["user", "admin"])
    _, resp = await app.asgi_client.get(
        "/me/", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status == 200
    assert resp.json["user"]["username"] == "alice"


async def test_scoped_admin_allows_admin_scope(app):
    token = _token(app, ["user", "admin"])
    _, resp = await app.asgi_client.get(
        "/me/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status == 200


async def test_scoped_admin_rejects_missing_scope(app):
    token = _token(app, ["user"])  # no admin scope
    _, resp = await app.asgi_client.get(
        "/me/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status == 403


async def test_protected_rejects_without_token(app):
    _, resp = await app.asgi_client.get("/me/")
    assert resp.status == 401
