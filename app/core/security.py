
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import (
    HashVerificationError,
    UnknownHashError,
)


load_dotenv()

JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Safely verify a password against its stored hash."""

    if not isinstance(hashed_password, str):
        return False

    # Reject disabled accounts and unsupported hashes.
    if not hashed_password.startswith("$argon2id$"):
        return False

    try:
        return password_hasher.verify(
            plain_password,
            hashed_password,
        )

    except (
        UnknownHashError,
        HashVerificationError,
        ValueError,
        TypeError,
    ):
        return False


def create_access_token(user_id: int) -> str:
    """Generate a signed JWT for an authenticated user."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is missing")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    """Validate a JWT and return its user ID."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is missing")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["sub", "iat", "exp"]
            },
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            raise ValueError("Invalid user ID")

        parsed_id = int(user_id)

        if parsed_id <= 0:
            raise ValueError("Invalid user ID")

        return parsed_id

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
    ) as exc:
        raise ValueError(
            "Invalid or expired access token"
        ) from exc
