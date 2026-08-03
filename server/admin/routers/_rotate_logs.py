"""
Log rotation & retention utility.

Rotates DB tables:
  - logs (older than retention.log_days) -> gz compressed JSONL under LOGS_ARCHIVE_DIR -> then DELETE
  - audit_logs (older than retention.audit_days) -> same archive, then DELETE
  - exfil_data (older than retention.exfil_days) -> DELETE permanently (don't archive, too big)

Rotates filesystem logs/*.log files (older than retention.fs_log_days) into LOGS_ARCHIVE_DIR.

Usage:
    # 手动跑
    python -m admin.routers._rotate_logs
    # 干跑模式（只打印不删不写）
    python -m admin.routers._rotate_logs --dry-run
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ADMIN_ROOT = PROJECT_ROOT / "admin"
sys.path.insert(0, str(ADMIN_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from admin.config_constants import (
    LOGS_ARCHIVE_DIR,
    STATE_DIR,
    cfg_int,
    cfg_str,
    default_of,
)

logger = logging.getLogger("rotate_logs")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _project_root(path_param: Optional[Path] = None) -> Path:
    return Path(path_param) if path_param else PROJECT_ROOT


def _get_archive_dir(root: Path) -> Path:
    d = LOGS_ARCHIVE_DIR if str(LOGS_ARCHIVE_DIR.parent) == str(root) else (root / "logs_archive")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_iso(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _row_to_dict(row, columns: list[str]) -> dict:
    d = {}
    for col in columns:
        d[col] = _to_iso(getattr(row, col, None))
    return d


def _stream_write_jsonl_gz(records: list[dict], gz_path: Path) -> int:
    """Write JSONL lines into a gz file.  Returns number of records written."""
    gz_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(str(gz_path), "wt", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def _rotate_db_logs(db: Session, root: Path, dry_run: bool = False,
                    logs_days: Optional[int] = None, audit_days: Optional[int] = None,
                    exfil_days: Optional[int] = None) -> dict:
    from admin.database import Log, AuditLog, ExfilData
    from sqlalchemy import and_, select, func

    logs_days = int(logs_days if logs_days is not None else cfg_int(db, "retention.log_days"))
    audit_days = int(audit_days if audit_days is not None else cfg_int(db, "retention.audit_days"))
    exfil_days = int(exfil_days if exfil_days is not None else cfg_int(db, "retention.exfil_days"))
    archive_batch_rows = max(100, int(cfg_int(db, "retention.archive_batch_rows")))
    delete_chunk_rows = max(50, int(cfg_int(db, "retention.delete_chunk_rows")))
    exfil_chunk_rows = max(100, int(cfg_int(db, "retention.exfil_delete_chunk_rows")))

    summary = {"logs_archived": 0, "logs_deleted": 0,
               "audit_archived": 0, "audit_deleted": 0,
               "exfil_deleted": 0}
    now = datetime.now()
    archive_dir = _get_archive_dir(root)
    day_tag = now.strftime("%Y%m%d")

    # -------------------- logs --------------------
    logs_cutoff = now - timedelta(days=logs_days)
    log_cols = ["id", "timestamp", "ip", "method", "path", "status_code",
                "content_length", "user_agent", "log_type", "device_uuid",
                "channel_id", "template_id"]
    total_logs = db.query(func.count(Log.id)).filter(Log.timestamp < logs_cutoff).scalar() or 0
    logger.info(f"[logs] records to rotate: {total_logs} (before {logs_cutoff.isoformat(timespec='minutes')})")
    if total_logs > 0:
        batch_size = archive_batch_rows
        offset = 0
        gz_path = archive_dir / f"logs_{day_tag}.jsonl.gz"
        file_suffix = 1
        while gz_path.exists():
            gz_path = archive_dir / f"logs_{day_tag}_{file_suffix}.jsonl.gz"
            file_suffix += 1
        all_log_ids = []
        written = 0
        while True:
            batch = (
                db.query(Log)
                .filter(Log.timestamp < logs_cutoff)
                .order_by(Log.id.asc())
                .offset(offset).limit(batch_size)
                .all()
            )
            if not batch:
                break
            records = [_row_to_dict(r, log_cols) for r in batch]
            if not dry_run:
                written += _stream_write_jsonl_gz(records, gz_path) if written == 0 else (
                    _stream_append_jsonl_gz(records, gz_path)
                )
            else:
                written += len(records)
            all_log_ids.extend(int(r.id) for r in batch)
            offset += len(batch)
            del batch
        summary["logs_archived"] = written
        if not dry_run and all_log_ids:
            # 分批删除，避免 SQLite too many SQL variables
            for i in range(0, len(all_log_ids), delete_chunk_rows):
                chunk = all_log_ids[i:i + delete_chunk_rows]
                db.query(Log).filter(Log.id.in_(chunk)).delete(synchronize_session=False)
            db.commit()
        summary["logs_deleted"] = len(all_log_ids)

    # -------------------- audit_logs --------------------
    audit_cutoff = now - timedelta(days=audit_days)
    audit_cols = ["id", "timestamp", "username", "action", "resource_type",
                  "resource_id", "detail", "ip_address", "user_agent"]
    total_audit = db.query(func.count(AuditLog.id)).filter(AuditLog.timestamp < audit_cutoff).scalar() or 0
    logger.info(f"[audit_logs] records to rotate: {total_audit} (before {audit_cutoff.isoformat(timespec='minutes')})")
    if total_audit > 0:
        batch_size = archive_batch_rows
        offset = 0
        gz_path = archive_dir / f"audit_logs_{day_tag}.jsonl.gz"
        sfx = 1
        while gz_path.exists():
            gz_path = archive_dir / f"audit_logs_{day_tag}_{sfx}.jsonl.gz"
            sfx += 1
        all_ids = []
        written = 0
        while True:
            batch = (
                db.query(AuditLog)
                .filter(AuditLog.timestamp < audit_cutoff)
                .order_by(AuditLog.id.asc())
                .offset(offset).limit(batch_size)
                .all()
            )
            if not batch:
                break
            records = [_row_to_dict(r, audit_cols) for r in batch]
            if not dry_run:
                if written == 0:
                    written += _stream_write_jsonl_gz(records, gz_path)
                else:
                    written += _stream_append_jsonl_gz(records, gz_path)
            else:
                written += len(records)
            all_ids.extend(int(r.id) for r in batch)
            offset += len(batch)
            del batch
        summary["audit_archived"] = written
        if not dry_run and all_ids:
            for i in range(0, len(all_ids), delete_chunk_rows):
                chunk = all_ids[i:i + delete_chunk_rows]
                db.query(AuditLog).filter(AuditLog.id.in_(chunk)).delete(synchronize_session=False)
            db.commit()
        summary["audit_deleted"] = len(all_ids)

    # -------------------- exfil_data (永久删除，不归档) --------------------
    exfil_cutoff = now - timedelta(days=exfil_days)
    total_exfil = db.query(func.count(ExfilData.id)).filter(ExfilData.uploaded_at < exfil_cutoff).scalar() or 0
    logger.info(f"[exfil_data] records to purge: {total_exfil} (before {exfil_cutoff.isoformat(timespec='minutes')})")
    if total_exfil > 0 and not dry_run:
        # 分批删除
        while True:
            ids_q = (
                select(ExfilData.id)
                .where(ExfilData.uploaded_at < exfil_cutoff)
                .order_by(ExfilData.id.asc())
                .limit(exfil_chunk_rows)
            )
            ids_rows = db.execute(ids_q).fetchall()
            ids = [int(r[0]) for r in ids_rows]
            if not ids:
                break
            db.query(ExfilData).filter(ExfilData.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            summary["exfil_deleted"] += len(ids)
            if len(ids) < exfil_chunk_rows:
                break
    else:
        summary["exfil_deleted"] = total_exfil

    return summary


def _stream_append_jsonl_gz(records: list[dict], gz_path: Path) -> int:
    """gzip doesn't really support append; we decompress + concatenate + re-gzip efficiently by streaming."""
    tmp = gz_path.with_suffix(gz_path.suffix + ".tmp")
    n = 0
    try:
        with gzip.open(str(gz_path), "rt", encoding="utf-8") as fr:
            with gzip.open(str(tmp), "wt", encoding="utf-8", newline="\n") as fw:
                for line in fr:
                    fw.write(line.rstrip("\n"))
                    fw.write("\n")
                    n += 1
                for rec in records:
                    fw.write(json.dumps(rec, ensure_ascii=False))
                    fw.write("\n")
                    n += 1
        tmp.replace(gz_path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    return n


def _rotate_fs_logs(root: Path, dry_run: bool = False, keep_days: Optional[int] = None) -> int:
    """Compress (gz) *.log files that haven't been modified in `keep_days` days into LOGS_ARCHIVE_DIR."""
    keep_days = int(keep_days if keep_days is not None else cfg_int(None, "retention.fs_log_days"))
    logs_dir = root / "logs"
    if not logs_dir.exists():
        return 0
    archive_dir = _get_archive_dir(root)
    cutoff = time.time() - keep_days * 86400
    compressed = 0
    for p in sorted(logs_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix == ".gz":
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime > cutoff:
            continue
        ts = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        target = archive_dir / f"{p.stem}_{ts}.log.gz"
        sfx = 1
        while target.exists():
            target = archive_dir / f"{p.stem}_{ts}_{sfx}.log.gz"
            sfx += 1
        if dry_run:
            logger.info(f"[fs] (dry-run) would gzip {p} -> {target}")
            compressed += 1
            continue
        try:
            with open(p, "rb") as fr, gzip.open(str(target), "wb") as fw:
                fw.write(fr.read())
            try:
                p.unlink()
            except OSError:
                logger.warning(f"[fs] cannot remove original log after gzip: {p}")
            compressed += 1
            logger.info(f"[fs] archived {p} -> {target.name}")
        except Exception:
            logger.exception(f"[fs] failed to archive {p}")
    return compressed


def rotate_all(db: Optional[Session] = None, project_root: Optional[Path] = None,
               dry_run: bool = False, **kwargs) -> dict:
    root = _project_root(project_root)
    summary = {"timestamp": datetime.now().isoformat(), "dry_run": dry_run}
    logs_days = kwargs.get("logs_days")
    audit_days = kwargs.get("audit_days")
    exfil_days = kwargs.get("exfil_days")
    # filesystem logs
    summary["fs_logs_archived"] = _rotate_fs_logs(root, dry_run=dry_run,
                                                   keep_days=logs_days if logs_days is not None else None)
    # DB logs
    if db is not None:
        summary["db"] = _rotate_db_logs(db, root, dry_run=dry_run,
                                         logs_days=logs_days,
                                         audit_days=audit_days,
                                         exfil_days=exfil_days)
    else:
        # Create a one-off DB session
        try:
            from admin.database import SessionLocal
            db2 = SessionLocal()
            try:
                summary["db"] = _rotate_db_logs(db2, root, dry_run=dry_run,
                                                 logs_days=logs_days,
                                                 audit_days=audit_days,
                                                 exfil_days=exfil_days)
            finally:
                db2.close()
        except Exception as e:
            logger.exception("Failed to rotate DB logs")
            summary["db"] = {"error": str(e)}
    logger.info(f"rotate_all summary: {json.dumps(summary, ensure_ascii=False)}")
    return summary


def _last_run_key(today: datetime) -> str:
    return today.strftime("%Y-%m-%d")


async def run_daily_if_needed(force: bool = False) -> Optional[dict]:
    """Lifespan cron helper: runs rotate_all() once per day at ~cron.rotate_start_hhmm.  Never raises."""
    try:
        from admin.database import SessionLocal
    except Exception:
        return None
    now = datetime.now()
    start_hhmm = cfg_str(None, "cron.rotate_start_hhmm")
    window_min = max(1, int(cfg_int(None, "cron.rotate_window_minutes")))
    try:
        hh_s, mm_s = start_hhmm.split(":")
        start_hour, start_minute = int(hh_s), int(mm_s)
    except Exception:
        start_hour, start_minute = 3, 30
    end_total = start_hour * 60 + start_minute + window_min
    end_hour, end_minute = (end_total // 60) % 24, end_total % 60
    now_total = now.hour * 60 + now.minute
    start_total = start_hour * 60 + start_minute
    # Only auto-run in the [start, start + window_min] window, unless force=True
    if not force and (now_total < start_total):
        return None
    if not force and (now_total >= (end_hour * 60 + end_minute)):
        return None
    root = _project_root()
    state_dir = Path(STATE_DIR) if str(STATE_DIR.parent.parent) == str(root) else (root / "logs_archive" / ".state")
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        state_dir = Path(root) / "logs" / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
    stamp_file = state_dir / f"rotate_{_last_run_key(now)}.ok"
    if stamp_file.exists() and not force:
        return None
    try:
        summary = rotate_all(project_root=root)
    except Exception:
        logger.exception("run_daily_if_needed failed")
        return None
    try:
        stamp_file.write_text(datetime.now().isoformat(), encoding="utf-8")
    except OSError:
        pass
    return summary


def _parse_args():
    parser = argparse.ArgumentParser(description="Rotate coruna logs (DB tables + disk files).")
    parser.add_argument("--dry-run", action="store_true", help="print only, no writes/deletes")
    def_log_days = int(default_of("retention.log_days") or 30)
    def_audit_days = int(default_of("retention.audit_days") or 90)
    def_exfil_days = int(default_of("retention.exfil_days") or 365)
    parser.add_argument("--logs-days", type=int, default=def_log_days)
    parser.add_argument("--audit-days", type=int, default=def_audit_days)
    parser.add_argument("--exfil-days", type=int, default=def_exfil_days)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    s = rotate_all(
        dry_run=args.dry_run,
        logs_days=args.logs_days,
        audit_days=args.audit_days,
        exfil_days=args.exfil_days,
    )
    print(json.dumps(s, ensure_ascii=False, indent=2))
