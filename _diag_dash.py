import sys, json, traceback
sys.path.insert(0, r"d:\wwwroot\coruna")
from fastapi.testclient import TestClient
from admin.main import app
client = TestClient(app)

r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

for url in ["/api/dashboard/summary", "/api/dashboard"]:
    print(f"\n=== GET {url} ===")
    try:
        r = client.get(url, headers=h, timeout=15)
        print("status:", r.status_code)
        if r.status_code != 200:
            print("body[:800]:", r.text[:800] if r.text else "empty")
        else:
            data = r.json()
            print("keys:", list(data.keys())[:10])
    except Exception as e:
        print("EXC:", repr(e))
        traceback.print_exc()
