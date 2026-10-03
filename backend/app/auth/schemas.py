"""Request and response shapes for login, tokens and users."""
from pydantic import BaseModel, Field

ROLES = ["manager", "agent", "analyst"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=2000)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72, description="At least 8 characters")


class CurrentUser(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    district: str | None = None
    agent_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires")
    user: CurrentUser
