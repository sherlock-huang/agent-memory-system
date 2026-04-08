@echo off
REM ============================================
REM  Experience File Server - 启动脚本
REM ============================================
REM
REM 使用方法:
REM   1. 确保云端服务器已启动
REM   2. 双击运行此脚本
REM

echo.
echo ========================================
echo   Experience File Server
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    pause
    exit /b 1
)
echo [OK] Python 已找到

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 启动服务器
echo 启动文件服务器 on port 8998...
echo 配置文件服务器地址: 218.201.18.131:8998
echo.
echo 按 Ctrl+C 停止服务器
echo.

python file_server.py
