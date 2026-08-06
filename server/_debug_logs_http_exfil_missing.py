"""
1:1 复现 devices.py get_device_logs 处理 HTTP/ExfilData 的逻辑
精确定位为什么 DB 有 47 条 HTTP + 6 条 exfil，但 summary 返回 http=0 / exfil=0
（异常被吞）
"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from admin.database import SessionLocal, Device, Log, Command, ExfilData
from sqlalchemy import desc as _desc
import re
from datetime import datetime, timedelta

uid = '4d8aaa92bdd06cd1044e7e242ef5b1c4'
db = SessionLocal()
device = db.query(Device).filter(Device.device_uuid == uid).first()
assert device, f"device {uid} not found!"
base_ip = (device.ip or '').strip() or None
print(f'Device ip={base_ip}, exploit_status={getattr(device,"exploit_status","?")}')

def _safe_str(v, max_len=300):
    try:
        if v is None: return ""
        s = str(v)
        if len(s) > max_len: s = s[:max_len] + f" ...(+{len(s) - max_len})"
        return s
    except Exception:
        return ""

def _evt(ts, kind, source, title, detail="", tags=None, ip=None, level="info", code=None, extra=None):
    if ts is None: return None
    if not isinstance(ts, datetime):
        try: ts = datetime.fromisoformat(str(ts).replace("Z", ""))
        except Exception as e:
            print(f'    _evt ts parse err: {e}')
            return None
    obj = {"time": ts.isoformat(), "type": kind or "misc", "source": source or "",
           "title": title or "", "detail": detail or "", "tags": list(tags or []),
           "level": level or "info"}
    if ip is not None: obj["ip"] = ip
    if code is not None: obj["status_code"] = int(code)
    if isinstance(extra, dict):
        for k, v in extra.items():
            if v is None: continue
            if k in ("time", "type", "source", "title", "detail", "tags", "level", "ip", "status_code"):
                continue
            obj[k] = v
    return obj

events = []
print('\n=== [1] HTTP logs processing (47 rows expected) ===')
limit, skip = 300, 0
http_count = 0
try:
    log_rows = (
        db.query(Log)
        .filter(Log.device_uuid == uid)
        .order_by(_desc(Log.timestamp))
        .limit(min(limit + 200, 800))
        .all()
    )
    print(f'  fetched rows: {len(log_rows)}')
    for idx, l in enumerate(log_rows):
        try:
            method = _safe_str(getattr(l, "method", None), 12) or "-"
            path = _safe_str(getattr(l, "path", None), 200) or "-"
            code = getattr(l, "status_code", None)
            lvl = "info"
            if code is not None:
                try:
                    c = int(code)
                    if c >= 500: lvl = "error"
                    elif c >= 400: lvl = "warn"
                except Exception:
                    pass
            log_type = _safe_str(getattr(l, "log_type", None), 20)
            ua = _safe_str(getattr(l, "user_agent", None), 120)
            title = f"{method} {path}"
            detail_parts = []
            if log_type: detail_parts.append(f"log_type={log_type}")
            if ua: detail_parts.append(f"ua={ua}")
            if code is not None: detail_parts.append(f"status={code}")
            clen = getattr(l, "content_length", None)
            if clen: detail_parts.append(f"bytes={clen}")
            evt = _evt(
                getattr(l, "timestamp", None),
                "http", log_type or "request",
                title, " | ".join(detail_parts),
                tags=[method] + ([log_type] if log_type else []),
                ip=getattr(l, "ip", None) or base_ip,
                level=lvl, code=code,
                extra={"method": method, "path": path, "ua": ua, "log_type": log_type,
                       "content_length": clen, "log_id": getattr(l, "id", None)},
            )
            if evt:
                events.append(evt)
                http_count += 1
            if idx < 3:
                print(f'  sample {idx}: ok -> time={evt and evt.get("time")} title={title[:60]}')
        except Exception as row_e:
            print(f'  !! HTTP ROW {idx} FAIL {type(row_e).__name__}: {row_e}')
            traceback.print_exc()
            break
except Exception as block_e:
    print(f'  !! HTTP BLOCK FAIL {type(block_e).__name__}: {block_e}')
    traceback.print_exc()
print(f'  -> http events appended: {http_count}')

print('\n=== [2] ExfilData processing (6 rows expected) ===')
exfil_count = 0
try:
    exfil_rows = (
        db.query(ExfilData)
        .filter(ExfilData.device_uuid == uid)
        .order_by(_desc(ExfilData.uploaded_at))
        .limit(min(limit + 100, 500))
        .all()
    )
    print(f'  fetched rows: {len(exfil_rows)}')
    for idx, e in enumerate(exfil_rows):
        try:
            cat = _safe_str(getattr(e, "category", None), 30) or "exfil"
            desc_t = _safe_str(getattr(e, "description", None), 200)
            fp = _safe_str(getattr(e, "file_path", None) or getattr(e, "path", None), 300)
            fs = getattr(e, "file_size", None)
            ts = getattr(e, "uploaded_at", None) or getattr(e, "created_at", None)
            fsize_h = ""
            if isinstance(fs, int):
                if fs < 1024: fsize_h = f"{fs} B"
                elif fs < 1024*1024: fsize_h = f"{fs/1024:.1f} KB"
                else: fsize_h = f"{fs/1024/1024:.2f} MB"
            title = f"[EXFIL {cat.upper()}] {desc_t or fp or '(no description)'}"
            detail_parts = []
            if cat: detail_parts.append(f"category={cat}")
            if fsize_h: detail_parts.append(f"size={fsize_h}")
            if fp: detail_parts.append(f"file={fp}")
            evt = _evt(
                ts, "exfil", f"exfil:{cat}",
                title, " | ".join(detail_parts),
                tags=[f"exfil:{cat}", "upload", "exfil"],
                ip=base_ip, level="success",
                extra={"category": cat, "description": desc_t, "file_path": fp,
                       "file_size": fs, "file_size_h": fsize_h,
                       "exfil_id": getattr(e, "id", None)},
            )
            if evt:
                events.append(evt)
                exfil_count += 1
            if idx < 3:
                print(f'  sample {idx}: ok -> time={evt and evt.get("time")} title={title[:60]}')
        except Exception as row_e:
            print(f'  !! EXFIL ROW {idx} FAIL {type(row_e).__name__}: {row_e}')
            traceback.print_exc()
            break
except Exception as block_e:
    print(f'  !! EXFIL BLOCK FAIL {type(block_e).__name__}: {block_e}')
    traceback.print_exc()
print(f'  -> exfil events appended: {exfil_count}')

print('\n=== [3] Summary after HTTP+Exfil ===')
summary = {"http":0,"command":0,"exfil":0,"device":0,"exploit":0,"exploit_console":0,"errors":0,"warnings":0,"success":0}
for ev in events:
    t = ev.get("type") or ""
    if t in summary: summary[t] += 1
    lv = (ev.get("level") or "").lower()
    if lv == "error": summary["errors"] += 1
    elif lv == "warn": summary["warnings"] += 1
    elif lv == "success": summary["success"] += 1
summary["total"] = len(events)
import json
print(json.dumps(summary, ensure_ascii=False, indent=2))
db.close()
