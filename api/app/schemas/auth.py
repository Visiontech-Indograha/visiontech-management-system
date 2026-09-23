from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str
    platform: str | None = "web"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: list[str]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str
