
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core import security


TEST_SECRET = "test-only-secret-key-for-jwt-security-tests"


@pytest.fixture
def jwt_secret(monkeypatch):
    """Use an isolated JWT secret for every test."""
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)


def test_password_hashing():
    password = "SecurePassword123!"

    hashed = security.hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert security.verify_password(password, hashed) is True


def test_incorrect_password():
    hashed = security.hash_password("CorrectPassword123!")

    assert security.verify_password(
        "WrongPassword123!",
        hashed,
    ) is False


def test_disabled_legacy_password():
    assert security.verify_password(
        "AnyPassword123!",
        "DISABLED",
    ) is False


def test_malformed_password_hash():
    assert security.verify_password(
        "AnyPassword123!",
        "$argon2id$invalid",
    ) is False


def test_create_and_decode_jwt(jwt_secret):
    token = security.create_access_token(user_id=42)

    assert isinstance(token, str)
    assert security.decode_access_token(token) == 42


def test_expired_jwt(jwt_secret):
    expired_token = jwt.encode(
        {
            "sub": "42",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        ValueError,
        match="Invalid or expired access token",
    ):
        security.decode_access_token(expired_token)


def test_tampered_jwt(jwt_secret):
    token = security.create_access_token(user_id=42)

    header, payload, signature = token.split(".")

    # Replace the signature with a different value.
    tampered_token = f"{header}.{payload}.{'A' * len(signature)}"

    with pytest.raises(ValueError):
        security.decode_access_token(tampered_token)


def test_jwt_missing_subject(jwt_secret):
    token = jwt.encode(
        {
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        security.decode_access_token(token)


def test_jwt_invalid_user_id(jwt_secret):
    token = jwt.encode(
        {
            "sub": "-1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        security.decode_access_token(token)


def test_jwt_wrong_secret(jwt_secret):
    token = jwt.encode(
        {
            "sub": "42",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        "different-secret-key-with-at-least-32-bytes",
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        security.decode_access_token(token)
