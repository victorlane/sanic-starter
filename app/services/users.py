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

# No ``from __future__ import annotations`` here: mayim reads each method's
# return annotation at runtime and needs the real class, not a string.

from mayim import PostgresExecutor, query

from app.models.user import User


class UserExecutor(PostgresExecutor):
    @query(
        """
        SELECT id, username, password_hash, scopes
        FROM users
        WHERE username = $username
        LIMIT 1;
        """
    )
    async def by_username(self, username: str) -> User | None: ...

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
    ) -> User: ...
