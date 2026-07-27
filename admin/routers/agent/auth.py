from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...database import get_db, Agent, Settings
from ...agent_auth import authenticate_agent, create_agent_access_token, get_current_agent, invalidate_agent_tokens
from ...utils.totp import verify_totp
from ... import config
from ...limiter import rate_limit
import secrets

router = APIRouter(prefix="/api/agent/auth", tags=["agent-auth"], redirect_slashes=False)

ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES
_agent_pending_2fa = {}


class AgentVerify2FARequest(BaseModel):
    temp_token: str
    otp_code: str


@rate_limit(config.AUTH_RATE_LIMIT)
@router.post("/login")
async def agent_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    agent = authenticate_agent(db, form_data.username, form_data.password)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect agent username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    require_2fa = db.query(Settings).filter(Settings.key == "security.require_2fa").first()
    require_2fa = (require_2fa.value if require_2fa else "false").lower() == "true"
    if require_2fa and agent.google_2fa_enabled == 1 and agent.google_2fa_secret:
        temp_token = secrets.token_urlsafe(32)
        _agent_pending_2fa[temp_token] = {
            "username": agent.username,
            "expires_at": datetime.now().timestamp() + 300
        }
        return {"requires_2fa": True, "temp_token": temp_token, "message": "2FA required"}
    agent.last_login = datetime.now()
    agent.last_login_ip = client_ip
    db.commit()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_agent_access_token(
        data={"sub": agent.username, "role": "agent", "agent_id": agent.id,
              "ver": getattr(agent, "token_version", 0) or 0, "type": "agent"},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "requires_2fa": False}


@rate_limit("30/minute")
@router.post("/verify-2fa")
async def agent_verify_2fa(request: Request, body: AgentVerify2FARequest, db: Session = Depends(get_db)):
    pending = _agent_pending_2fa.get(body.temp_token)
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid temp token")
    if datetime.now().timestamp() > pending["expires_at"]:
        del _agent_pending_2fa[body.temp_token]
        raise HTTPException(status_code=400, detail="Temp token expired")
    agent = db.query(Agent).filter(Agent.username == pending["username"]).first()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found")
    if not verify_totp(agent.google_2fa_secret, body.otp_code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    del _agent_pending_2fa[body.temp_token]
    agent.last_login = datetime.now()
    agent.last_login_ip = request.client.host if request.client else None
    db.commit()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_agent_access_token(
        data={"sub": agent.username, "role": "agent", "agent_id": agent.id,
              "ver": getattr(agent, "token_version", 0) or 0, "type": "agent"},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def agent_me(current_agent: Agent = Depends(get_current_agent)):
    return {
        "id": current_agent.id, "username": current_agent.username,
        "name": current_agent.name, "contact": current_agent.contact,
        "phone": current_agent.phone, "enabled": int(current_agent.enabled if current_agent.enabled is not None else 1),
        "max_devices": current_agent.max_devices or 0,
        "commission_rate": current_agent.commission_rate or 0,
        "last_login": current_agent.last_login.isoformat() if current_agent.last_login else None,
        "created_at": current_agent.created_at.isoformat() if current_agent.created_at else None,
    }


@router.post("/logout")
async def agent_logout(
    request: Request,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    invalidate_agent_tokens(db, current_agent)
    return {"message": "Logged out successfully"}
