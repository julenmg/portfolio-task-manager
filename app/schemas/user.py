from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, value: str) -> str:
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must contain only letters, numbers, hyphens, or underscores")
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        errors: list[str] = []
        if not any(c.isupper() for c in value):
            errors.append("at least one uppercase letter")
        if not any(c.islower() for c in value):
            errors.append("at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            errors.append("at least one digit")
        if errors:
            raise ValueError(f"Password must contain {', '.join(errors)}")
        return value


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
