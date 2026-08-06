import sys
sys.path.insert(0, '.')
from datetime import datetime, timedelta as _td
from sqlalchemy import or_ as _or, and_ as _and
from admin.database import SessionLocal, Command

uuid = "ios-4a0d2f80840d7442667e3947"
ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"

# Check is_safari_browser
ua_stripped = (ua or "").strip()
is_safari = bool(ua_stripped) and "Safari/" in ua_stripped and "NativeC2" not in ua_stripped and "powerd" not in ua_stripped and "Exploit-Server" not in ua_stripped
print(f"is_safari_browser = {is_safari}")
print(f"  - bool(ua_stripped) = {bool(ua_stripped)}")
print(f"  - 'Safari/' in ua = {'Safari/' in ua_stripped}")
print(f"  - 'NativeC2' not in ua = {'NativeC2' not in ua_stripped}")
print(f"  - 'powerd' not in ua = {'powerd' not in ua_stripped}")
print(f"  - 'Exploit-Server' not in ua = {'Exploit-Server' not in ua_stripped}")

# Direct query for pending commands
db = SessionLocal()
try:
    commands = db.query(Command).filter(
        Command.device_uuid == uuid,
        _or(
            Command.status == 'pending',
            _and(
                Command.status == 'deferred',
                Command.executed_at.is_(None),
            ),
            _and(
                Command.status == 'deferred',
                Command.executed_at.is_not(None),
                Command.executed_at <= datetime.now() - _td(seconds=30),
            ),
        ),
    ).order_by(Command.created_at).all()
    print(f"\nDirect query result: {len(commands)} commands")
    for c in commands:
        print(f"  ID={c.id} | STATUS={c.status}")
finally:
    db.close()

# Also check what statuses exist
db2 = SessionLocal()
try:
    all_statuses = db2.query(Command.status, Command.id).filter(Command.device_uuid == uuid).all()
    print(f"\nAll statuses: {all_statuses}")
finally:
    db2.close()
