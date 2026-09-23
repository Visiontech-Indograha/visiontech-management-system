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
    query = text("SELECT id, email, password_hash, role, status, login_attempts, is_locked FROM vms.users WHERE email = :email")
    result = await db.execute(query, {"email": request.email})
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=400, detail="Email atau kata sandi salah")
        
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan")
        
    if user.is_locked:
        raise HTTPException(status_code=403, detail="Akun terkunci karena terlalu banyak percobaan gagal")
        
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Email atau kata sandi salah")
        
    # Create session
    session_id = str(uuid.uuid4())
    
    token_data = {
        "sub": str(user.id),
        "role": user.role,
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
        role = payload.get("role")
        session_id = payload.get("jti")
        
        # In a real app, verify that session_id is still valid in DB
        
        token_data = {
            "sub": user_id,
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
    query = text("SELECT email, role FROM vms.users WHERE id = :id")
    result = await db.execute(query, {"id": current_user.user_id})
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserMeResponse(
        user_id=current_user.user_id,
        email=user.email,
        role=user.role,
        permissions=current_user.permissions
    )
