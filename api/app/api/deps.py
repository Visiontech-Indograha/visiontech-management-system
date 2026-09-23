from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from typing import List

from app.core.config import settings
from app.core.permissions import Permission, get_role_permissions
from app.core.security import verify_jwt_token

security = HTTPBearer()

class CurrentUser(BaseModel):
    user_id: str
    organization_id: str
    email: str
    role: str
    session_id: str
    permissions: List[str]

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = verify_jwt_token(token)
        user_id = payload.get("sub")
        org_id = payload.get("org")
        email = payload.get("email", "unknown")
        role = payload.get("role", "field")
        session_id = payload.get("jti")
        
        if user_id is None or org_id is None or session_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
            
        permissions = get_role_permissions(role)
        return CurrentUser(
            user_id=user_id,
            organization_id=org_id,
            email=email,
            role=role,
            session_id=session_id,
            permissions=permissions
        )
    except Exception:
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
    query = text("""
        SET LOCAL app.user_id = :uid;
        SET LOCAL app.organization_id = :org_id;
        SET LOCAL app.actor_label = :actor;
    """)
    await db.execute(query, {
        "uid": current_user.user_id,
        "org_id": current_user.organization_id,
        "actor": current_user.email
    })
    return db

