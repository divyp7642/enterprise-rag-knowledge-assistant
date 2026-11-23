
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.main import app
from app.services.auth_service import (
    InvalidCredentialsError,
    RegistrationConflictError,
)


REGISTER_PAYLOAD = {
    "organization_name": "Test Company",
    "email": "admin@test.example",
    "password": "SecurePassword123!",
}

LOGIN_PAYLOAD = {
    "email": "admin@test.example",
    "password": "SecurePassword123!",
}


def test_register_success():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        with patch(
            "app.api.auth.register_organization",
            return_value={
                "user_id": 10,
                "organization_id": 5,
                "email": "admin@test.example",
                "organization_name": "Test Company",
                "message": "Registration successful",
            },
        ) as mock_register:
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json=REGISTER_PAYLOAD,
                )

            assert response.status_code == 201
            assert response.json()["user_id"] == 10
            assert response.json()["organization_id"] == 5
            mock_register.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_register_duplicate():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        with patch(
            "app.api.auth.register_organization",
            side_effect=RegistrationConflictError(
                "Email is already registered"
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json=REGISTER_PAYLOAD,
                )

            assert response.status_code == 409
            assert response.json()["detail"] == (
                "Email is already registered"
            )

    finally:
        app.dependency_overrides.clear()


def test_login_success():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        with patch(
            "app.api.auth.authenticate_user",
            return_value={
                "access_token": "test-jwt-token",
                "token_type": "bearer",
            },
        ) as mock_authenticate:
            with TestClient(app) as client:
                response = client.post(
                    "/auth/login",
                    json=LOGIN_PAYLOAD,
                )

            assert response.status_code == 200
            assert response.json()["access_token"] == (
                "test-jwt-token"
            )
            assert response.json()["token_type"] == "bearer"
            mock_authenticate.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_login_invalid_credentials():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        with patch(
            "app.api.auth.authenticate_user",
            side_effect=InvalidCredentialsError(
                "Invalid email or password"
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/login",
                    json=LOGIN_PAYLOAD,
                )

            assert response.status_code == 401
            assert response.json()["detail"] == (
                "Invalid email or password"
            )

    finally:
        app.dependency_overrides.clear()


def test_me_without_token():
    with TestClient(app) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication token"
    )


def test_me_authenticated():
    fake_user = SimpleNamespace(
        id=10,
        email="admin@test.example",
        organization_id=5,
    )

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )

    try:
        with TestClient(app) as client:
            response = client.get("/auth/me")

        assert response.status_code == 200
        assert response.json() == {
            "user_id": 10,
            "email": "admin@test.example",
            "organization_id": 5,
        }

    finally:
        app.dependency_overrides.clear()
