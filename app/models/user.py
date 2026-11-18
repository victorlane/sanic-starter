from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import BigInteger, DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """The ``users`` table. ``password_hash`` is never serialized to clients.

    This class is the schema: change it, then generate a migration with
    ``alembic revision --autogenerate`` (see README "Models and migrations").
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    username: str = Field(sa_type=Text, unique=True)
    password_hash: str = Field(sa_type=Text)
    scopes: list[str] = Field(
        default_factory=list,
        sa_type=ARRAY(Text),
        sa_column_kwargs={"server_default": text("'{}'")},
    )
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )


class LoginPayload(BaseModel):
    username: str
    password: str


class RegisterPayload(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
