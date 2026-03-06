---
description: 如何部署修复后的代码到生产服务器
---

# 部署修复指南

为了使图片在 `https://www.qjzxmd.cn/images` 正常显示，你需要将更改应用到生产服务器。

## 步骤 1: 更新 Nginx 配置 (立即生效)
这将允许 Nginx 直接处理旧的图片路径，解决 404 问题。

1. 将修改后的 `server/nginx/host_lock_app.conf` 内容更新到服务器上的 Nginx 配置文件中。
2. 重新加载 Nginx：
   ```bash
   sudo nginx -s reload
   ```

## 步骤 2: 重启后端服务 (永久修复)
这将使 API 开始返回正确的 `/uploads/` 路径。

1. 确保生产服务器上的代码已同步（包括 `server/app/api/images.py` 和 `server/app/ws/handler.py`）。
2. 重启 Docker 容器：
   ```bash
   cd server
   docker-compose up --build -d
   ```

## 步骤 3: 强制刷新浏览器
清除可能的 404 缓存：
- Mac: `Cmd + Shift + R`
- Windows/Linux: `Ctrl + F5`
