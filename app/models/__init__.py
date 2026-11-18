"""Models. Import every table model here so Alembic's autogenerate sees it."""

from app.models.user import User

__all__ = ["User"]
