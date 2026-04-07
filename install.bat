@echo off
REM ============================================
REM  Agent Memory System - Windows 一键安装脚本
REM ============================================
REM
REM 使用方法:
REM   1. 双击运行此脚本
REM   2. 等待安装完成
REM

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Agent Memory System 安装向导
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先从 https://python.org 安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已找到

REM 检查 pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 pip
    echo 请重新安装 Python，确保勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] pip 已找到

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 安装依赖
echo.
echo [1/5] 安装 Python 依赖...
pip install pyyaml mysql-connector-python --quiet >nul 2>&1
if errorlevel 1 (
    echo [错误] 依赖安装失败
    echo 请以管理员身份运行此脚本
    pause
    exit /b 1
)
echo [OK] 依赖安装完成

REM 检查配置文件
if not exist "config.yaml" (
    echo.
    echo [2/5] 配置文件不存在，使用默认配置
    (
        echo # Agent Memory System - Configuration
        echo.
        echo database:
        echo   type: mysql
        echo   host: "218.201.18.131"
        echo   port: 8999
        echo   database: "agent_memory"
        echo   user: "root1"
        echo   password: "lJ0^)sG0\dI1~gN1"lJ6^|"
        echo   charset: "utf8mb4"
        echo.
        echo source: "cli"
        echo agent_id: null
        echo.
        echo search:
        echo   default_limit: 10
        echo   max_limit: 100
        echo.
        echo log_level: "INFO"
    ) > config.yaml
) else (
    echo [2/5] 配置文件已存在，跳过
)

REM 创建经验目录
echo.
echo [3/5] 创建本地存储目录...
if not exist "experiences" mkdir experiences
if not exist "logs" mkdir logs
echo [OK] 目录创建完成

REM 初始化数据库表
echo.
echo [4/5] 初始化数据库表...
python src\cli\memory_cli.py status >nul 2>&1
if errorlevel 1 (
    echo [警告] 数据库连接失败
    echo 请检查 config.yaml 中的数据库配置
) else (
    echo [OK] 数据库连接成功
)

REM 测试存储功能
echo.
echo [5/5] 测试存储功能...
echo [测试] 这是一条测试记忆 | python src\cli\memory_cli.py store "本地测试记忆" --type general --tags test >nul 2>&1
if errorlevel 1 (
    echo [警告] 存储测试失败
) else (
    echo [OK] 存储功能正常
)

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 常用命令:
echo.
echo   查看状态:     python src\cli\memory_cli.py status
echo   存储记忆:    python src\cli\memory_cli.py store "内容"
echo   分享经验:    python src\cli\memory_cli.py share-experience --help
echo   查询云端:    python src\cli\memory_cli.py cloud-query "关键词"
echo   列出经验:    python src\cli\memory_cli.py list-shared
echo.
echo 详细文档: README.md
echo 快速上手: QUICKSTART.md
echo.
pause
