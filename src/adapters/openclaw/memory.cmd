@echo off
REM Memory CLI Wrapper for Windows
REM 用法: memory.cmd <command> [args]

setlocal

REM 设置 Python 路径
set PYTHON=C:\Users\openclaw-windows-2\AppData\Local\Programs\Python\Python312\python.exe

REM 设置 Memory CLI 路径
set MEMORY_CLI=%~dp0memory_skill.py

REM 执行
"%PYTHON%" "%MEMORY_CLI%" %*

endlocal
