from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db, User, create_audit_log
from ..auth import get_current_user, invalidate_user_tokens
from ..utils.totp import generate_secret, verify_totp, get_provisioning_uri
from .settings import _set_setting
from ..limiter import rate_limit

router = APIRouter(prefix="/api/auth/2fa", tags=["2fa"], redirect_slashes=False)


class Enable2FARequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)


class Verify2FARequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)


@router.get("/setup")
@rate_limit("10/minute")
async def setup_2fa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.google_2fa_enabled == 1:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    secret = generate_secret()
    uri = get_provisioning_uri(secret, current_user.username)
    current_user.google_2fa_secret = secret
    current_user.google_2fa_enabled = 0
    db.commit()
    return {"secret": secret, "provisioning_uri": uri, "username": current_user.username}


@router.post("/enable")
@rate_limit("10/minute")
async def enable_2fa(
    request: Request,
    body: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.google_2fa_enabled == 1:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    if not current_user.google_2fa_secret:
        raise HTTPException(status_code=400, detail="Please call /setup first to generate a secret")
    if not verify_totp(current_user.google_2fa_secret, body.token):
        raise HTTPException(status_code=400, detail="Invalid 2FA token")
    current_user.google_2fa_enabled = 1
    db.commit()
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db, username=current_user.username, action="2fa_enabled",
        resource_type="auth", detail="User enabled Google 2FA",
        ip_address=client_ip
    )
    return {"message": "2FA enabled successfully"}


@router.post("/verify")
@rate_limit("30/minute")
async def verify_2fa(
    request: Request,
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.google_2fa_enabled != 1 or not current_user.google_2fa_secret:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    if not verify_totp(current_user.google_2fa_secret, body.token):
        raise HTTPException(status_code=400, detail="Invalid 2FA token")
    return {"valid": True}


@router.post("/disable")
@rate_limit("5/minute")
async def disable_2fa(
    request: Request,
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.google_2fa_enabled != 1:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    if not verify_totp(current_user.google_2fa_secret, body.token):
        raise HTTPException(status_code=400, detail="Invalid 2FA token")
    current_user.google_2fa_enabled = 0
    current_user.google_2fa_secret = None
    _set_setting(db, "security.require_2fa", "false", "强制开启2FA", current_user.username)
    db.commit()
    invalidate_user_tokens(db, current_user)
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db, username=current_user.username, action="2fa_disabled",
        resource_type="auth", detail="User disabled Google 2FA",
        ip_address=client_ip
    )
    return {"message": "2FA disabled successfully"}


@router.get("/status")
async def get_2fa_status(current_user: User = Depends(get_current_user)):
    return {
        "enabled": current_user.google_2fa_enabled == 1,
        "has_secret": bool(current_user.google_2fa_secret)
    }
