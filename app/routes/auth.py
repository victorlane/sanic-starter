"""Auth routes: register + login.

Demonstrates, together:
- ``@validate(json=Model)``  — validates the body AND documents it in OpenAPI.
- ``UserExecutor`` injected by type annotation (DI via mayim/sanic-ext).
- ``@ratelimit`` from the fork's security battery on the login endpoint.
- ``@openapi.*``            — enriches the auto-generated spec.
"""

from __future__ import annotations

from sanic import Blueprint, Request, json
from sanic.security import ratelimit
from sanic_ext import openapi, validate

from app.models.user import LoginPayload, RegisterPayload, TokenResponse
from app.security import hash_password, issue_token, verify_password
from app.services.users import UserExecutor


auth = Blueprint("auth", url_prefix="/auth")


@auth.post("/register")
@openapi.tag("auth")
@openapi.summary("Register a new user")
@openapi.body(RegisterPayload)
@openapi.response(201, {"application/json": TokenResponse}, "Created")
@validate(json=RegisterPayload)
async def register(request: Request, body: RegisterPayload, users: UserExecutor):
    existing = await users.by_username(body.username)
    if existing is not None:
        return json({"error": "username taken"}, status=409)

    row = await users.create(
        username=body.username,
        password_hash=hash_password(body.password),
        scopes=["user"],
    )
    token = issue_token(
        request, {"sub": row.id, "username": row.username, "scopes": row.scopes}
    )
    return json({"token": token}, status=201)


@auth.post("/login")
# Brute-force protection: 5 attempts per client IP, refilled every 60s. Excess
# requests get a 429 before ever touching the database. NOTE: the in-memory
# backend is per-worker; use a shared backend for a global limit across workers.
@ratelimit(5, 60)
@openapi.tag("auth")
@openapi.summary("Exchange credentials for a JWT")
@openapi.body(LoginPayload)
@openapi.response(200, {"application/json": TokenResponse}, "OK")
@validate(json=LoginPayload)
async def login(request: Request, body: LoginPayload, users: UserExecutor):
    row = await users.by_username(body.username)
    if row is None or not verify_password(body.password, row.password_hash):
        return json({"error": "invalid credentials"}, status=401)

    token = issue_token(
        request, {"sub": row.id, "username": row.username, "scopes": row.scopes}
    )
    return json({"token": token})
