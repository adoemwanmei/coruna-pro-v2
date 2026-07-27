import sys
sys.path.insert(0, r'd:\wwwroot\coruna')
from admin.database import SessionLocal, Settings

db = SessionLocal()
try:
    updates = {
        "security.require_2fa": "true",
        "security.twofa_users": "true",
    }
    for k, v in updates.items():
        s = db.query(Settings).filter(Settings.key == k).first()
        if s:
            s.value = v
        else:
            s = Settings(key=k, value=v, description="auto test", updated_by="system")
            db.add(s)
        print(f"  Set {k} = {v}")
    db.commit()
    print("DB updated")
finally:
    db.close()
