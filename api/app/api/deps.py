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

from collections.abc import AsyncIterator
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.context import set_request_context
from app.db.session import AsyncSessionLocal
from app.db.transaction import unit_of_work

# "function": commit/rollback terjadi SEBELUM respons dikirim, jadi commit yang gagal
# sampai ke klien sebagai 500 — bukan 200 untuk data yang ternyata tidak tersimpan.
DB_SCOPE: Literal["function", "request"] = "function"


async def get_db() -> AsyncIterator[AsyncSession]:
    """Satu permintaan = satu transaksi: commit bila handler sukses, rollback bila galat (T-02)."""
    async with AsyncSessionLocal() as session:
        async with unit_of_work(session):
            yield session

async def get_db_with_user(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_current_user)
) -> AsyncSession:
    # Konteks RLS & audit untuk transaksi permintaan ini (app/db/context.py).
    try:
        await set_request_context(
            db,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            actor_label=current_user.email,
        )
    except Exception as e:
        from app.core.alerts import send_security_alert
        await send_security_alert("Konteks RLS Gagal Disetel", f"Gagal menetapkan context RLS untuk user {current_user.email}. DB Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return db

