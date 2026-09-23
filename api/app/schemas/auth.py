from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: List[str]
