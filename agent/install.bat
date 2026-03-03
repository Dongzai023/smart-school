@echo off
chcp 65001 >nul
echo ========================================
echo  希沃一体机管理 Agent 安装脚本
echo ========================================
echo.

REM 检查 Python 是否已安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 正在安装依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)

REM 创建缓存目录
echo [2/3] 正在创建缓存目录...
if not exist "cache" mkdir cache

REM 提示修改配置
echo [3/3] 安装完成!
echo.
echo ========================================
echo  请编辑 config.yaml 配置以下信息:
echo    - server.host: 管理服务器IP地址
echo    - agent_key: 设备密钥(从管理后台获取)
echo ========================================
echo.
echo  配置完成后，运行以下命令启动Agent:
echo    python agent.py
echo.
pause
