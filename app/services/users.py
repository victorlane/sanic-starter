"""mayim executor for the users table.

mayim is a *hydrator*, not an ORM: each method carries SQL (here via the
``@query`` decorator; you can equally drop a matching ``.sql`` file under
``app/queries/``) and mayim maps the result rows onto the annotated return
type. Method bodies are intentionally empty (``...``).

This executor is registered on the app via ``SanicMayimExtension`` (see
``app/server.py``) and is then **injected into route handlers by type
annotation** — that is the dependency-injection story: a handler simply
declares ``users: UserExecutor`` and mayim supplies it per request.
"""

from __future__ import annotations

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

    @query(
        """
        INSERT INTO users (username, password_hash, scopes)
        VALUES ($username, $password_hash, $scopes)
        RETURNING id, username, password_hash, scopes;
        """
    )
    async def create(
        self,
        username: str,
        password_hash: str,
        scopes: list[str],
    ) -> UserRow: ...
