# sanic-starter

An opinionated starter for building an API with Sanic. It wires up JWT
auth, Postgres access via mayim, OpenAPI docs, and a small security
battery, then gets out of the way.

## What's included

- App factory (`app/server.py`) that builds and configures the Sanic app.
- JWT auth with scopes (`app/security.py`, `app/routes/auth.py`,
  `app/routes/me.py`): register, login, `@protected`, `@require_scopes`.
- Postgres access via mayim, injected into route handlers by type
  annotation (`app/services/users.py`).
- OpenAPI spec and docs UI via sanic-ext, including a bearer security
  scheme for the protected routes.
- Security headers and trusted-host enforcement, on by default.
- Optional Redis-backed sessions (`app/sessions.py`), inert unless
  `REDIS_URL` is set.
- Optional Prometheus `/metrics` endpoint (`app/metrics.py`), inert
  unless `METRICS_ENABLED` is set.
- Tests with an in-memory fake executor, so the suite runs without a
  real Postgres (`tests/test_auth.py`).
- ruff for linting and ty for type checking, both run in CI.

## Getting started

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
cp .env.example .env
```

Fill in `APP_SECRET` in `.env` (see the comment in that file for how to
generate one). Start Postgres, either with Docker:

```bash
docker compose up -d db
```

or point `POSTGRES_DSN` at an existing instance, then apply the schema:

```bash
psql "$POSTGRES_DSN" -f schema.sql
```

Run the dev server:

```bash
uv run sanic app.server:app --dev
```

The API is now at `http://localhost:8000`, with docs at `/docs` and the
OpenAPI spec at `/docs/openapi.json` (set `OAS=false` to disable both in
production).

### Checks

```bash
uv run pytest -q        # tests (no Postgres needed)
uv run ruff check .     # lint
uv run ty check .       # type check
```

## Lay of the land

```
app/
  server.py        app factory: config, extensions, DI, routes
  security.py       password hashing, JWT issue/decode, @protected, @require_scopes
  sessions.py        optional Redis-backed sessions
  metrics.py          optional Prometheus /metrics endpoint
  models/
    user.py           plain dataclasses for request/response bodies
  routes/
    auth.py           POST /auth/register, POST /auth/login
    me.py             GET /me, GET /me/admin (protected examples)
  services/
    users.py          mayim executor for the users table
  queries/              place for standalone .sql files (see mayim below)
tests/
  test_auth.py          smoke tests against an in-memory fake executor
schema.sql              minimal Postgres schema for the starter
docker-compose.yml       Postgres (and optionally Redis) for local dev
```

## mayim, in brief

mayim is a data-access library, not an ORM. Rather than a query builder
or an active-record layer, it is a *hydrator*: you write SQL yourself,
mayim runs it, and it maps the result rows onto whatever type you
annotated the method to return.

An executor is a class holding related queries. Its methods are
annotated with a return type and left with an empty body (`...`); mayim
fills them in at runtime. `app/services/users.py` looks like this:

```python
from dataclasses import dataclass
from mayim import PostgresExecutor, query


@dataclass
class UserRow:
    id: int
    username: str
    password_hash: str
    scopes: list[str]


class UserExecutor(PostgresExecutor):
    @query(
        """
        SELECT id, username, password_hash, scopes
        FROM users
        WHERE username = $username
        LIMIT 1;
        """
    )
    async def by_username(self, username: str) -> UserRow | None: ...
```

Calling `await users.by_username("alice")` runs that SQL with
`username` bound from the argument and returns either a `UserRow` or
`None`, matching the annotation. `$username` in the query is a mayim
placeholder bound to the `username` parameter by name, not raw string
interpolation, so this is safe against SQL injection the same way a
parameterized query anywhere else would be.

If a query gets long, drop it in `app/queries/` as a `.sql` file with a
matching name instead of inlining it in the decorator; mayim picks it up
the same way.

The executor is registered once, in `app/server.py`:

```python
Extend.register(SanicMayimExtension(executors=[UserExecutor], dsn=dsn))
```

and from there it is available for dependency injection: a handler
just declares a parameter annotated `UserExecutor` and mayim supplies an
instance per request, no manual wiring at the call site.

```python
async def register(request: Request, body: RegisterPayload, users: UserExecutor):
    existing = await users.by_username(body.username)
    ...
```

In tests, the same injection point makes it easy to swap in a fake: see
`FakeUsers` in `tests/test_auth.py`, an in-memory subclass of
`UserExecutor` that overrides the same methods so the rest of the app
never notices it isn't talking to Postgres.

## Optional extras

- `uv sync --extra redis` for Redis-backed sessions, then set `REDIS_URL`.
- `uv sync --extra metrics` for the Prometheus endpoint, then set
  `METRICS_ENABLED=true`.

Both are no-ops when their env var is unset, and their dependencies are
only imported once the feature is actually turned on.
