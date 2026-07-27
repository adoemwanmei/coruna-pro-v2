from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import secrets

from ..database import get_db, User, init_db, create_audit_log, Settings
from ..auth import authenticate_user, create_access_token, get_password_hash, get_current_user, invalidate_user_tokens
from ..utils.totp import verify_totp
from ..schemas import Token, UserResponse
from .. import config
from ..limiter import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"], redirect_slashes=False)

ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES
_pending_2fa = {}


class Verify2FARequest(BaseModel):
    temp_token: str
    otp_code: str


@rate_limit(config.AUTH_RATE_LIMIT)
@router.post("/login")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if not user:
        create_audit_log(
            db, username=form_data.username, action="login_failed",
            resource_type="auth", detail=f"Failed login attempt from IP {client_ip}",
            ip_address=client_ip, user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    require_2fa = db.query(Settings).filter(Settings.key == "security.require_2fa").first()
    require_2fa = (require_2fa.value if require_2fa else "false").lower() == "true"

    if require_2fa and user.google_2fa_enabled == 1 and user.google_2fa_secret:
        temp_token = secrets.token_urlsafe(32)
        _pending_2fa[temp_token] = {
            "username": user.username,
            "expires_at": datetime.now().timestamp() + 300
        }
        create_audit_log(
            db, username=user.username, action="login_2fa_required",
            resource_type="auth", detail=f"User requires 2FA verification from IP {client_ip}",
            ip_address=client_ip, user_agent=user_agent
        )
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
            "message": "2FA verification required"
        }

    user.last_login = datetime.now()
    db.commit()

    create_audit_log(
        db, username=user.username, action="login_success",
        resource_type="auth", detail=f"User logged in from IP {client_ip}",
        ip_address=client_ip, user_agent=user_agent
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "ver": getattr(user, "token_version", 0) or 0, "type": "admin"},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "requires_2fa": False}


@rate_limit("30/minute")
@router.post("/verify-2fa")
async def verify_login_2fa(
    request: Request,
    body: Verify2FARequest,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    pending = _pending_2fa.get(body.temp_token)
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired temp token")
    if datetime.now().timestamp() > pending["expires_at"]:
        del _pending_2fa[body.temp_token]
        raise HTTPException(status_code=400, detail="Temp token expired")

    user = db.query(User).filter(User.username == pending["username"]).first()
    if not user:
        del _pending_2fa[body.temp_token]
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_totp(user.google_2fa_secret, body.otp_code):
        create_audit_log(
            db, username=user.username, action="login_2fa_failed",
            resource_type="auth", detail=f"2FA verification failed from IP {client_ip}",
            ip_address=client_ip
        )
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    del _pending_2fa[body.temp_token]
    user.last_login = datetime.now()
    db.commit()

    create_audit_log(
        db, username=user.username, action="login_success",
        resource_type="auth", detail=f"User logged in with 2FA from IP {client_ip}",
        ip_address=client_ip, user_agent=request.headers.get("user-agent")
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "ver": getattr(user, "token_version", 0) or 0, "type": "admin"},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    invalidate_user_tokens(db, current_user)
    create_audit_log(
        db, username=current_user.username, action="logout",
        resource_type="auth", detail=f"User logged out from IP {client_ip}",
        ip_address=client_ip, user_agent=request.headers.get("user-agent")
    )
    return {"message": "Logged out successfully"}


@router.post("/init")
@rate_limit("3/minute")
async def init_admin(request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    if client_ip not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin init only allowed from localhost. Please access via 127.0.0.1 / ::1."
        )
    existing_any = db.query(User).first()
    if existing_any is not None:
        init_db()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin already initialized. If you forgot password, reset via DB directly."
        )
    init_db()
    admin = User(username="admin", password=get_password_hash("admin123"), role="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)
    create_audit_log(
        db, username="system", action="admin_init",
        resource_type="auth",
        detail=f"Default admin created from IP {client_ip}. Please change password immediately.",
        ip_address=client_ip
    )
    return {"message": "Admin user created (change password immediately!)", "user": admin.username}
