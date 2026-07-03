"""Optional Redis-backed sessions.

Toggle with the ``REDIS_URL`` env var: set it and sessions are enabled; leave
it unset and this module is inert (no Redis dependency touched, no middleware
installed). Uses the modern ``redis.asyncio`` client (redis-py), not the
abandoned ``aioredis``.

Design mirrors the small store shape proven by ``sanic-session``:
``_get``/``_set``/``_delete`` over an opaque session id, with cookie handling
layered on top. A signed, ``HttpOnly`` cookie carries only the session id; the
data lives in Redis.

Usage (in the app factory)::

    from app.sessions import install_sessions
    install_sessions(app)  # no-op unless REDIS_URL is configured

Then in a handler::

    request.ctx.session["count"] = request.ctx.session.get("count", 0) + 1
"""

from __future__ import annotations

import json

from os import getenv
from uuid import uuid4

from sanic import Request, Sanic
from sanic.response import HTTPResponse


COOKIE = "session"
TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


class RedisSessionStore:
    """Minimal async session store over redis.asyncio."""

    def __init__(self, url: str, prefix: str = "session:") -> None:
        # Imported lazily so the dependency is only needed when sessions are on.
        from redis.asyncio import from_url

        self._redis = from_url(url, decode_responses=True)
        self._prefix = prefix

    async def _get(self, sid: str) -> dict:
        raw = await self._redis.get(self._prefix + sid)
        return json.loads(raw) if raw else {}

    async def _set(self, sid: str, data: dict) -> None:
        await self._redis.set(
            self._prefix + sid, json.dumps(data), ex=TTL_SECONDS
        )

    async def _delete(self, sid: str) -> None:
        await self._redis.delete(self._prefix + sid)


def install_sessions(app: Sanic) -> None:
    """Install session middleware iff ``REDIS_URL`` is configured.

    Safe to call unconditionally: without ``REDIS_URL`` it does nothing and the
    ``redis`` package is never imported.
    """
    url = getenv("REDIS_URL")
    if not url:
        return

    store = RedisSessionStore(url)

    @app.on_request
    async def _open_session(request: Request) -> None:
        sid = request.cookies.get(COOKIE)
        if sid:
            request.ctx.session = await store._get(sid)
            request.ctx.session_id = sid
        else:
            request.ctx.session = {}
            request.ctx.session_id = uuid4().hex

    @app.on_response
    async def _save_session(request: Request, response: HTTPResponse) -> None:
        session = getattr(request.ctx, "session", None)
        if session is None:
            return
        sid = request.ctx.session_id
        if session:
            await store._set(sid, session)
            response.add_cookie(
                COOKIE,
                sid,
                httponly=True,
                samesite="Lax",
                secure=request.scheme == "https",
                max_age=TTL_SECONDS,
            )
        else:
            # Empty session: drop it.
            await store._delete(sid)
            if COOKIE in request.cookies:
                response.delete_cookie(COOKIE)
