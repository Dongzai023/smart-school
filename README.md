# 希沃一体机统一管理系统

[![Deploy to Tencent Cloud](https://github.com/Dongzai023/lock-screen/actions/workflows/deploy.yml/badge.svg)](https://github.com/Dongzai023/lock-screen/actions/workflows/deploy.yml)

统一管理教室希沃 (Seewo) 一体机的自动锁屏、解锁和关机。

## 功能特性

- 🖥️ **设备管理** — 添加/分组管理 36+ 台一体机
- ⏰ **时间策略** — 按周配置自动锁屏/解锁/关机时间
- 🖼️ **锁屏画面** — 后台上传管理锁屏背景图
- 🔐 **手动控制** — 一键锁屏/解锁/关机（单台或批量）
- 👩‍🏫 **教师解锁** — 教师临时申请解锁，管理员审批
- 📋 **操作日志** — 全部操作记录可追溯

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.0 + Redis |
| 前端 | Vue 3 + Element Plus |
| Agent | Python + tkinter + WebSocket (WSS) |
| 部署 | Docker Compose + Nginx + GitHub Actions CI/CD |

## 架构

```
希沃一体机 Agent ──── WSS (公网) ────→ 腾讯云服务器
   教室 1~36                            ├── Nginx (SSL)
                                        ├── FastAPI API
管理员/教师浏览器 ──── HTTPS ──────────→ ├── MySQL 8
                                        └── Redis
```

## 项目结构

```
lock-screen/
├── server/          # 后端 (FastAPI + Docker)
├── web/             # 管理后台 (Vue 3)
├── agent/           # 设备端 Agent (Windows)
└── .github/         # CI/CD 工作流
```

## 部署指南

### 1. 云服务器初始化

```bash
# SSH 到腾讯云服务器
ssh root@your-server-ip

# 创建部署目录
mkdir -p /opt/lock-screen/server

# 进入目录，创建 .env 配置
cd /opt/lock-screen/server
cp .env.example .env
nano .env  # 修改数据库密码、JWT密钥等

# 配置 SSL 证书
mkdir -p nginx/ssl
# 将 fullchain.pem 和 privkey.pem 放入 nginx/ssl/
```

### 2. GitHub Secrets 配置

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 腾讯云服务器公网 IP |
| `SERVER_USER` | SSH 用户名（如 root） |
| `SSH_PRIVATE_KEY` | SSH 私钥内容 |

### 3. 自动部署

推送代码到 `main` 分支会自动触发 GitHub Actions：
- 构建 Vue 前端
- 同步文件到服务器
- 重建 Docker 容器

### 4. Agent 部署到一体机

1. 将 `agent/` 复制到希沃一体机
2. 运行 `install.bat`
3. 编辑 `config.yaml`：
   - `server.host`: 云服务器公网 IP 或域名
   - `agent_key`: 从管理后台获取的设备密钥
4. 运行 `python agent.py`

## 默认账号

- 用户名: `admin` / 密码: `admin123`
- ⚠️ 请登录后立即修改密码
