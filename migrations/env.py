"""Alembic environment.

The models in ``app/models`` are the schema. ``alembic revision
--autogenerate`` diffs them against the database named by ``POSTGRES_DSN``
and writes a migration; ``alembic upgrade head`` applies pending ones.
"""

from os import getenv

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers every table on the metadata)

load_dotenv()

target_metadata = SQLModel.metadata


def _url() -> str:
    dsn = getenv(
        "POSTGRES_DSN", "postgres://postgres:postgres@localhost:5432/app"
    )
    # mayim takes a plain libpq DSN; SQLAlchemy needs the driver spelled out.
    scheme, _, rest = dsn.partition("://")
    if scheme in ("postgres", "postgresql"):
        return f"postgresql+psycopg://{rest}"
    return dsn


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of connecting (``alembic upgrade --sql``)."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
