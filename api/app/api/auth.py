from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse
from app.core.security import verify_password, create_jwt_token
from app.api.deps import CurrentUser, get_current_user
from datetime import timedelta
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
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
        # TODO: Increment login_attempts and check lockout
        raise HTTPException(status_code=400, detail="Email atau kata sandi salah")
        
    # TODO: Reset login_attempts
    
    # Create session in DB
    session_id = str(uuid.uuid4())
    # TODO: insert into vms.sessions
    
    # Generate token
    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "jti": session_id
    }
    access_token = create_jwt_token(token_data, timedelta(hours=8))
    
    return TokenResponse(access_token=access_token)

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
