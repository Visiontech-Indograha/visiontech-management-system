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
async def login(request: LoginRequest, req: Request, response: Response, db: AsyncSession = Depends(get_db)):
    ip = req.client.host if req.client else None
    agent = req.headers.get("user-agent", "Unknown")
    
    # 1. Cek pembatasan login
    lock_query = text("SELECT vms.login_is_locked(:email)")
    is_locked = (await db.execute(lock_query, {"email": request.email})).scalar()
    if is_locked:
        from app.core.alerts import send_security_alert
        await send_security_alert("Lonjakan Kegagalan Login", f"Akun {request.email} terkunci sementara dari IP {ip}.")
        raise HTTPException(status_code=403, detail={"code": "LOCKED", "message": "Terlalu banyak kegagalan login. Coba lagi nanti."})
    
    # Fetch user
    query = text("""
        SELECT u.id, u.login, u.password_hash, u.is_active, u.organization_id, r.role
        FROM vms.app_user u
        LEFT JOIN vms.user_role r ON u.id = r.user_id
        WHERE u.login = :email
    """)
    result = await db.execute(query, {"email": request.email})
    user = result.fetchone()
    
    if not user or not verify_password(request.password, user.password_hash):
        log_attempt = text("INSERT INTO vms.login_attempt (login, ip_address, successful, reason) VALUES (:email, :ip, false, 'Invalid credentials')")
        await db.execute(log_attempt, {"email": request.email, "ip": ip})
        raise HTTPException(status_code=400, detail={"code": "INVALID_CREDENTIALS", "message": "Email atau kata sandi salah"})
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "INACTIVE", "message": "Akun dinonaktifkan"})
        
    # Sukses login
    log_attempt = text("INSERT INTO vms.login_attempt (login, ip_address, successful) VALUES (:email, :ip, true)")
    await db.execute(log_attempt, {"email": request.email, "ip": ip})
    
    # Isu Sesi ke DB
    issue_query = text("""
        SELECT session_id, family_id, refresh_token, expires_at 
        FROM vms.issue_session(:org, :user_id, 'Web Login', 'fingerprint', :ip, :agent)
    """)
    sess = await db.execute(issue_query, {
        "org": user.organization_id,
        "user_id": user.id,
        "ip": ip,
        "agent": agent
    })
    session_data = sess.fetchone()
    
    token_data = {
        "sub": str(user.id),
        "org": str(user.organization_id),
        "email": user.login,
        "role": user.role or "field",
        "jti": str(session_data.session_id)
    }
    
    # 15 minutes access token
    access_token = create_jwt_token(token_data, timedelta(minutes=15))
    set_refresh_cookie(response, session_data.refresh_token)
    
    return TokenResponse(access_token=access_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = req.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "NO_TOKEN", "message": "No refresh token found"})
        
    ip = req.client.host if req.client else None
    agent = req.headers.get("user-agent", "Unknown")
    
    # Rotasi sesi di DB
    rot_query = text("SELECT session_id, user_id, refresh_token, expires_at, reused FROM vms.rotate_session(:rt, :ip, :agent)")
    rot = await db.execute(rot_query, {"rt": refresh_token, "ip": ip, "agent": agent})
    rot_data = rot.fetchone()
    
    if not rot_data or rot_data.reused:
        if rot_data and rot_data.reused:
            from app.core.alerts import send_security_alert
            await send_security_alert("Pencurian Sesi (Reuse Detected)", f"Refresh token usang dipakai oleh IP {ip}. Seluruh sesi perangkat dicabut.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SESSION_REVOKED", "message": "Sesi tidak valid atau telah dicabut"})
        
    if not rot_data.session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN", "message": "Token tidak valid"})
        
    # Get user profile for new JWT
    query = text("""
        SELECT u.id, u.login, u.organization_id, r.role 
        FROM vms.app_user u
        LEFT JOIN vms.user_role r ON u.id = r.user_id
        WHERE u.id = :uid
    """)
    user_res = await db.execute(query, {"uid": rot_data.user_id})
    user = user_res.fetchone()
    
    token_data = {
        "sub": str(user.id),
        "org": str(user.organization_id),
        "email": user.login,
        "role": user.role or "field",
        "jti": str(rot_data.session_id)
    }
    
    access_token = create_jwt_token(token_data, timedelta(minutes=15))
    set_refresh_cookie(response, rot_data.refresh_token)
    
    return TokenResponse(access_token=access_token)

@router.post("/logout")
async def logout(req: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = req.cookies.get("refresh_token")
    if refresh_token:
        query = text("UPDATE vms.user_session SET state = 'REVOKED', revoked_at = now(), revoked_reason = 'User logged out' WHERE refresh_sha256 = digest(:rt, 'sha256')")
        await db.execute(query, {"rt": refresh_token})
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
