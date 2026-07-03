"""Application factory.

Run with:  sanic app.server:app  (or `uv run sanic app.server:app`)
"""

from __future__ import annotations

from os import getenv

from dotenv import load_dotenv
from mayim.extension import SanicMayimExtension
from sanic import Sanic
from sanic.security import enable_security
from sanic_ext import Extend

from app.metrics import install_metrics
from app.routes.auth import auth
from app.routes.me import me
from app.services.users import UserExecutor
from app.sessions import install_sessions


load_dotenv()


def create_app(name: str = "SanicStarter", *, use_db: bool = True) -> Sanic:
    """Build the app.

    Args:
        name: App name (unique per instance).
        use_db: When ``False``, the mayim/Postgres extension is not registered
            so no real connection pool is opened — tests set this and inject a
            fake ``UserExecutor`` instead.
    """
    app = Sanic(name)

    # --- config ---
    app.config.SECRET = getenv("APP_SECRET", "change-me")
    app.config.SECURITY_HEADERS = _bool(getenv("SECURITY_HEADERS"), True)
    trusted = getenv("TRUSTED_HOSTS")
    if trusted:
        app.config.TRUSTED_HOSTS = [
            h.strip() for h in trusted.split(",") if h.strip()
        ]
    # OpenAPI: set OAS=false in production to disable the spec + docs UIs.
    app.config.OAS = _bool(getenv("OAS"), True)

    # --- extensions (sanic-ext must be attached before app.ext / DI) ---
    Extend(app)
    app.ext.openapi.describe(
        "Sanic Starter API",
        version="0.1.0",
        description="Starter API — JWT auth, mayim/Postgres, DI, OpenAPI.",
    )
    # Register the bearer security scheme referenced by @openapi.secured("token").
    app.ext.openapi.add_security_scheme(
        "token", "http", scheme="bearer", bearer_format="JWT"
    )

    # --- dependency injection: mayim executors become injectable by type ---
    if use_db:
        dsn = getenv(
            "POSTGRES_DSN", "postgres://postgres:postgres@localhost:5432/app"
        )
        Extend.register(
            SanicMayimExtension(executors=[UserExecutor], dsn=dsn)
        )

    # --- security battery (headers + trusted-host enforcement) ---
    enable_security(app)

    # --- optional Redis sessions (no-op unless REDIS_URL is set) ---
    install_sessions(app)

    # --- optional Prometheus metrics (no-op unless METRICS_ENABLED) ---
    install_metrics(app)

    # --- routes ---
    app.blueprint(auth)
    app.blueprint(me)

    return app


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


app = create_app()
