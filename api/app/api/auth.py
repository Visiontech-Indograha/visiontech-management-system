from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse
from app.core.security import verify_password, create_jwt_token, verify_jwt_token
from app.api.deps import CurrentUser, get_current_user, get_db
from datetime import timedelta
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

def set_refresh_cookie(response: Response, token: str):
    # Setting max_age to 7 days for the refresh token
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Fetch user
    query = text("""
        SELECT u.id, u.login, u.password_hash, u.is_active, u.organization_id, r.role
        FROM vms.app_user u
        LEFT JOIN vms.user_role r ON u.id = r.user_id
        WHERE u.login = :email
    """)
    result = await db.execute(query, {"email": request.email})
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=400, detail="Email atau kata sandi salah")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan")
        
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Email atau kata sandi salah")
        
    # Create session
    session_id = str(uuid.uuid4())
    
    token_data = {
        "sub": str(user.id),
        "org": str(user.organization_id),
        "email": user.login,
        "role": user.role or "field",
        "jti": session_id
    }
    
    # 15 minutes access token
    access_token = create_jwt_token(token_data, timedelta(minutes=15))
    # 7 days refresh token
    refresh_token = create_jwt_token(token_data, timedelta(days=7))
    
    set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(access_token=access_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token found")
        
    try:
        payload = verify_jwt_token(refresh_token)
        user_id = payload.get("sub")
        org_id = payload.get("org")
        email = payload.get("email")
        role = payload.get("role")
        session_id = payload.get("jti")
        
        token_data = {
            "sub": user_id,
            "org": org_id,
            "email": email,
            "role": role,
            "jti": session_id
        }
        
        # New 15 minutes access token
        access_token = create_jwt_token(token_data, timedelta(minutes=15))
        return TokenResponse(access_token=access_token)
        
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Retrieve latest user info
    query = text("""
        SELECT u.login, r.role 
        FROM vms.app_user u
        LEFT JOIN vms.user_role r ON u.id = r.user_id
        WHERE u.id = :id
    """)
    result = await db.execute(query, {"id": current_user.user_id})
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserMeResponse(
        user_id=current_user.user_id,
        email=user.login,
        role=user.role or "field",
        permissions=current_user.permissions
    )

from pydantic import BaseModel

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password", response_model=TokenResponse)
async def change_password(request: ChangePasswordRequest, response: Response, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = text("SELECT password_hash FROM vms.app_user WHERE id = :id")
    result = await db.execute(query, {"id": current_user.user_id})
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Data yang dikirim tidak valid.", "details": {"fields": {"current_password": "Password saat ini salah."}}})
        
    from app.core.security import hash_password
    hashed_new = hash_password(request.new_password)
    
    update_query = text("UPDATE vms.app_user SET password_hash = :hash WHERE id = :id")
    await db.execute(update_query, {"hash": hashed_new, "id": current_user.user_id})
    
    # Generate new tokens
    session_id = str(uuid.uuid4())
    token_data = {
        "sub": current_user.user_id,
        "org": current_user.organization_id,
        "email": current_user.email,
        "role": current_user.role,
        "jti": session_id
    }
    
    access_token = create_jwt_token(token_data, timedelta(minutes=15))
    refresh_token = create_jwt_token(token_data, timedelta(days=7))
    
    set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(access_token=access_token)
