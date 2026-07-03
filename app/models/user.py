from dataclasses import dataclass, field


@dataclass
class User:
    """A user row. ``password_hash`` is never serialized to clients."""

    id: int
    username: str
    scopes: list[str] = field(default_factory=list)


@dataclass
class LoginPayload:
    username: str
    password: str


@dataclass
class RegisterPayload:
    username: str
    password: str


@dataclass
class TokenResponse:
    token: str
