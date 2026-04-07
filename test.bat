@echo off
REM ============================================
REM Agent Memory System - 快速测试脚本
REM ============================================

echo.
echo ========================================
echo   Agent Memory System - 连接测试
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查配置文件...
if not exist "config.yaml" (
    echo [警告] config.yaml 不存在，复制模板...
    copy config.yaml.example config.yaml
)

echo.
echo [2/3] 测试数据库连接...
python src\cli\memory_cli.py status

echo.
echo [3/3] 测试存储功能...
echo 这是一条测试记忆 | python src\cli\memory_cli.py store "这是一条测试记忆" --type general --tags test

echo.
echo ========================================
echo   测试完成！
echo ========================================
echo.
echo 常用命令:
echo   python src\cli\memory_cli.py list
echo   python src\cli\memory_cli.py status
echo   python src\cli\memory_cli.py share-experience --help
echo.
pause
