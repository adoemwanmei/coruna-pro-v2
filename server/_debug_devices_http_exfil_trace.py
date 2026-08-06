"""
最小复现：在 devices.py HTTP block 中，把 except Exception: pass 去掉，显式 print traceback
看真实 FastAPI 里为什么 Log/ExfilData 块抛异常
"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from admin.database import SessionLocal, Device, Log, ExfilData
from sqlalchemy import desc as _desc
from admin.routers.devices import _safe_str, _evt

uid = '4d8aaa92bdd06cd1044e7e242ef5b1c4'
db = SessionLocal()
device = db.query(Device).filter(Device.device_uuid == uid).first()
base_ip = (device.ip or "").strip() or None
events = []
limit, skip = 300, 0

print('===== 1) HTTP block with traceback enable =====')
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
                except Exception: pass
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
            if evt: events.append(evt)
            if idx < 2:
                print(f'  row {idx} ok title={title[:50]}')
        except Exception as row_e:
            print(f'!! ROW {idx} FAIL: {type(row_e).__name__}: {row_e}')
            traceback.print_exc()
            break
except Exception as block_e:
    print(f'!! HTTP BLOCK FAIL: {type(block_e).__name__}: {block_e}')
    traceback.print_exc()

print('===== 2) ExfilData block with traceback enable =====')
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
            desc = _safe_str(getattr(e, "description", None), 200)
            fp = _safe_str(getattr(e, "file_path", None) or getattr(e, "path", None), 300)
            fs = getattr(e, "file_size", None)
            ts = getattr(e, "uploaded_at", None) or getattr(e, "created_at", None)
            fsize_h = ""
            if isinstance(fs, int):
                if fs < 1024: fsize_h = f"{fs} B"
                elif fs < 1024*1024: fsize_h = f"{fs/1024:.1f} KB"
                else: fsize_h = f"{fs/1024/1024:.2f} MB"
            title = f"[EXFIL {cat.upper()}] {desc or fp or '(no description)'}"
            detail_parts = []
            if cat: detail_parts.append(f"category={cat}")
            if fsize_h: detail_parts.append(f"size={fsize_h}")
            if fp: detail_parts.append(f"file={fp}")
            evt = _evt(
                ts, "exfil", f"exfil:{cat}",
                title, " | ".join(detail_parts),
                tags=[f"exfil:{cat}", "upload", "exfil"],
                ip=base_ip, level="success",
                extra={"category": cat, "description": desc, "file_path": fp,
                       "file_size": fs, "file_size_h": fsize_h,
                       "exfil_id": getattr(e, "id", None)},
            )
            if evt: events.append(evt)
            if idx < 2:
                print(f'  row {idx} ok title={title[:50]}')
        except Exception as row_e:
            print(f'!! EXFIL ROW {idx} FAIL: {type(row_e).__name__}: {row_e}')
            traceback.print_exc()
            break
except Exception as block_e:
    print(f'!! EXFIL BLOCK FAIL: {type(block_e).__name__}: {block_e}')
    traceback.print_exc()

print(f'\n[Result] events={len(events)}')
types = {}
for ev in events:
    t = ev.get("type") or "?"
    types[t] = types.get(t, 0) + 1
print(f'  Type breakdown: {types}')
db.close()
