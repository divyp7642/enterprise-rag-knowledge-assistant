
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    organization_name: str = Field(
        min_length=2,
        max_length=255,
    )

    email: str = Field(
        min_length=3,
        max_length=255,
    )

    password: str = Field(
        min_length=12,
        max_length=128,
    )

    @field_validator("organization_name")
    @classmethod
    def validate_organization_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Organization name must contain at least 2 characters"
            )

        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if (
            "@" not in value
            or value.startswith("@")
            or value.endswith("@")
            or any(character.isspace() for character in value)
        ):
            raise ValueError("Invalid email address")

        return value


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    organization_id: int
    email: str
    organization_name: str
    message: str = "Registration successful"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
