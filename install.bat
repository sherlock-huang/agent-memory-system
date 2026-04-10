@echo off
REM ============================================
REM Agent Memory System - Windows 安装脚本
REM ============================================

echo.
echo ============================================
echo   Agent Memory System 安装程序
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 检查 Python 版本...
python --version

echo.
echo [2/5] 安装依赖...
pip install pymysql cryptography yaml

echo.
echo [3/5] 创建配置目录...
if not exist "%USERPROFILE%\.openclaw\workspace" mkdir "%USERPROFILE%\.openclaw\workspace"
if not exist "%USERPROFILE%\.memory" mkdir "%USERPROFILE%\.memory"

echo.
echo [4/5] 复制配置文件...
if exist "config.yaml.example" (
    if not exist "config.yaml" (
        copy "config.yaml.example" "config.yaml"
        echo [提示] 已创建 config.yaml，请编辑配置数据库连接信息
    )
)

echo.
echo [5/5] 安装完成！
echo.
echo ============================================
echo   下一步操作：
echo ============================================
echo.
echo 1. 设置数据库环境变量（推荐）：
echo.
echo    $env:MEMORY_DB_HOST = "your-mysql-host.com"
echo    $env:MEMORY_DB_PASSWORD = "your_password"
echo.
echo 2. 或者编辑 config.yaml 配置数据库连接
echo.
echo 3. 初始化数据库：
echo    mysql -h YOUR_HOST -u YOUR_USER -p agent_memory ^< scripts\init_mysql.sql
echo.
echo 4. 运行测试：
echo    python -m skills.agent-memory.scripts.client status
echo.
echo ============================================
pause
