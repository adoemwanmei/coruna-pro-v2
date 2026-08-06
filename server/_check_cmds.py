import sqlite3
conn = sqlite3.connect('darksword.db')
cur = conn.cursor()
cur.execute('SELECT id, device_uuid, command, status, output, executed_at, created_at FROM commands WHERE device_uuid LIKE "%4a0d%" ORDER BY id DESC LIMIT 15')
rows = cur.fetchall()
for r in rows:
    print(f"ID={r[0]} | CMD={r[2][:40]:<40} | STATUS={r[3]:<12} | OUTPUT={str(r[4])[:60]:<60} | EXEC={r[5]} | CREATED={r[6]}")
conn.close()
