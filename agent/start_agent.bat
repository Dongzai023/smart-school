@echo off
chcp 65001 >nul
REM ========================================
REM  希沃一体机管理 Agent 启动脚本
REM ========================================

REM 获取脚本所在目录
cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python
    pause
    exit /b 1
)

REM 启动 Agent
echo [INFO] 启动 Agent...
python agent.py
