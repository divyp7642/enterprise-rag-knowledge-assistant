
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest


class RegistrationConflictError(Exception):
    """Raised when registration conflicts with existing data."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are incorrect."""


def register_organization(
    db: Session,
    request: RegisterRequest,
) -> dict:
    """Register a new organization and its first user."""

    organization_name = request.organization_name.strip()
    email = request.email.strip().lower()

    existing_organization = db.scalar(
        select(Organization).where(
            func.lower(Organization.name) == organization_name.lower()
        )
    )

    if existing_organization is not None:
        raise RegistrationConflictError(
            "Organization name is already registered"
        )

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise RegistrationConflictError(
            "Email is already registered"
        )

    password_hash = hash_password(request.password)

    try:
        organization = Organization(
            name=organization_name
        )

        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            email=email,
            password_hash=password_hash,
        )

        db.add(user)
        db.flush()

        result = {
            "user_id": user.id,
            "organization_id": organization.id,
            "email": user.email,
            "organization_name": organization.name,
            "message": "Registration successful",
        }

        db.commit()
        return result

    except IntegrityError as exc:
        db.rollback()
        raise RegistrationConflictError(
            "Email or organization is already registered"
        ) from exc

    except Exception:
        db.rollback()
        raise


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> dict:
    """Verify credentials and issue a JWT access token."""

    normalized_email = email.strip().lower()

    user = db.scalar(
        select(User).where(
            User.email == normalized_email
        )
    )

    if user is None:
        raise InvalidCredentialsError(
            "Invalid email or password"
        )

    if not verify_password(
        password,
        user.password_hash,
    ):
        raise InvalidCredentialsError(
            "Invalid email or password"
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
