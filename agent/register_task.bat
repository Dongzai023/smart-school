@echo off
chcp 65001 >nul
echo ========================================
echo  注册 Agent 为 Windows 开机自启任务
echo  (需要以管理员身份运行)
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 请右键此脚本，选择"以管理员身份运行"
    echo.
    pause
    exit /b 1
)

REM 获取脚本所在目录
set AGENT_DIR=%~dp0
set AGENT_DIR=%AGENT_DIR:~0,-1%

REM 获取 Python 路径
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i
if "%PYTHON_PATH%"=="" (
    echo [ERROR] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo [INFO] Agent目录: %AGENT_DIR%
echo [INFO] Python路径: %PYTHON_PATH%
echo.

REM 删除旧任务（如果存在）
schtasks /delete /tn "SeewoLockAgent" /f >nul 2>&1

REM 创建计划任务
REM   /sc ONLOGON  = 用户登录时启动
REM   /rl HIGHEST  = 以最高权限运行
REM   /delay 0000:30 = 登录后延迟30秒启动（等待网络就绪）
schtasks /create ^
    /tn "SeewoLockAgent" ^
    /tr "\"%PYTHON_PATH%\" \"%AGENT_DIR%\agent.py\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /delay 0000:30 ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  [OK] 注册成功!
    echo ========================================
    echo.
    echo  任务名称: SeewoLockAgent
    echo  触发方式: 用户登录后30秒自动启动
    echo  运行权限: 最高权限
    echo.
    echo  你可以通过以下方式管理此任务:
    echo    查看: schtasks /query /tn "SeewoLockAgent"
    echo    删除: schtasks /delete /tn "SeewoLockAgent" /f
    echo    手动运行: schtasks /run /tn "SeewoLockAgent"
    echo.
) else (
    echo.
    echo [ERROR] 注册失败，请检查权限
    echo.
)

pause
