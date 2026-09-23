from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from typing import List

from app.core.config import settings
from app.core.permissions import Permission, get_role_permissions

security = HTTPBearer()

class CurrentUser(BaseModel):
    user_id: str
    role: str
    session_id: str
    permissions: List[str]

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    token = credentials.credentials
    try:
        # TODO: Decode using EdDSA and verify with DB if session revoked
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"]) # Change to EdDSA
        user_id = payload.get("sub")
        role = payload.get("role", "field")
        session_id = payload.get("jti")
        
        if user_id is None or session_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
            
        permissions = get_role_permissions(role)
        return CurrentUser(
            user_id=user_id,
            role=role,
            session_id=session_id,
            permissions=permissions
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

def require_permission(required_permission: Permission):
    def permission_checker(current_user: CurrentUser = Depends(get_current_user)):
        if required_permission.value not in current_user.permissions and "admin" != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user
    return permission_checker

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_with_user(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> AsyncSession:
    # Pass user context to Postgres for RLS and auditing
    await db.execute(text("SET LOCAL vms.user_id = :uid"), {"uid": current_user.user_id})
    return db

