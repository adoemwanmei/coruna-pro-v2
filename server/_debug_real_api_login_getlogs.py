"""
100% 真实复现：登录 FastAPI admin 7000 → 拿 JWT token → 请求 /api/devices/{uuid}/logs
精确打印 summary 和 events 前 10 条 type
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import requests
from urllib.parse import urljoin

BASE = "http://127.0.0.1:7000"
UID = "4d8aaa92bdd06cd1044e7e242ef5b1c4"
USER, PASS = "admin", "admin123"

s = requests.Session()
print(f"[1] 登录 {BASE}/api/auth/login  username={USER}")
r = s.post(urljoin(BASE, "/api/auth/login"), data={"username": USER, "password": PASS})
print(f"    status={r.status_code}  body={r.text[:500]}")
r.raise_for_status()
tok = r.json().get("access_token")
assert tok, "no token!"
print(f"    token OK len={len(tok)}  cookie={s.cookies.get_dict()}")

url = urljoin(BASE, f"/api/devices/{UID}/logs")
print(f"\n[2] GET {url}?limit=500&skip=0")
r2 = s.get(url, params={"limit": 500, "skip": 0}, headers={"Authorization": f"Bearer {tok}"})
print(f"    status={r2.status_code}  len={len(r2.content)}")
if r2.status_code != 200:
    print(f"    body={r2.text[:2000]}")
    sys.exit(1)
data = r2.json()
print("\n[3] Summary:")
import json
print(json.dumps(data.get("summary", {}), ensure_ascii=False, indent=2))
dbg = data.get("_dbg") or data.get("summary", {}).get("_dbg") or None
if dbg:
    print("\n[3b] _dbg (instrumentation):")
    print(json.dumps(dbg, ensure_ascii=False, indent=2))
else:
    print("\n[3b] _dbg = None — FastAPI 进程未加载最新代码")
print(f"\n[4] Total events: {len(data.get('events', []))}")
types = {}
for ev in data.get("events", []):
    t = ev.get("type", "?")
    types[t] = types.get(t, 0) + 1
print(f"    Type breakdown: {json.dumps(types, ensure_ascii=False)}")
print("\n[5] First 20 events (sample (time/type/source/title[:60]):")
for i, ev in enumerate(data.get("events", [])[:20]):
    t = ev.get("time", "")[:26]
    ty = ev.get("type", "")
    src = ev.get("source", "")
    title = (ev.get("title", "") or "")[:60]
    print(f"  {i:02d} {ty:14s} | {src:18s} | {t} | {title}")
print("\n[6] Last 15 events:")
for i, ev in enumerate(data.get("events", [])[-15:]):
    t = ev.get("time", "")[:26]
    ty = ev.get("type", "")
    src = ev.get("source", "")
    title = (ev.get("title", "") or "")[:60]
    print(f"  {i:02d} {ty:14s} | {src:18s} | {t} | {title}")
