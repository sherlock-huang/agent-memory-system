@echo off
REM ============================================
REM  Agent Memory System - Windows 涓€閿畨瑁呰剼鏈?REM ============================================
REM
REM 浣跨敤鏂规硶:
REM   1. 鍙屽嚮杩愯姝よ剼鏈?REM   2. 绛夊緟瀹夎瀹屾垚
REM

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Agent Memory System 瀹夎鍚戝
echo ========================================
echo.

REM 妫€鏌?Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [閿欒] 鏈壘鍒?Python
    echo 璇峰厛浠?https://python.org 瀹夎 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 宸叉壘鍒?
REM 妫€鏌?pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [閿欒] 鏈壘鍒?pip
    echo 璇烽噸鏂板畨瑁?Python锛岀‘淇濆嬀閫?"Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] pip 宸叉壘鍒?
REM 鑾峰彇鑴氭湰鐩綍
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 瀹夎渚濊禆
echo.
echo [1/6] 瀹夎 Python 渚濊禆...
pip install pyyaml mysql-connector-python boto3 --quiet >nul 2>&1
if errorlevel 1 (
    echo [璀﹀憡] 閮ㄥ垎渚濊禆瀹夎澶辫触锛屽皾璇曞崟鐙畨瑁?..
    pip install pyyaml --quiet >nul 2>&1
    pip install mysql-connector-python --quiet >nul 2>&1
    pip install boto3 --quiet >nul 2>&1
)
echo [OK] 渚濊禆瀹夎瀹屾垚

REM 妫€鏌ラ厤缃枃浠?if not exist "config.yaml" (
    echo.
    echo [2/6] 鍒涘缓閰嶇疆鏂囦欢...
    (
        echo # Agent Memory System - Configuration
        echo.
        echo # MinIO 浜戠瀛樺偍
        echo minio:
        echo   endpoint: "218.201.18.133:8010"
        echo   access_key: "admin"
        echo   secret_key: "Minio12345678"
        echo   bucket: "openclaw"
        echo   region: "cn-east-1"
        echo.
        echo # MySQL 鏁版嵁搴?        echo database:
        echo   type: mysql
        echo   host: "218.201.18.133"
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
    echo [2/6] 閰嶇疆鏂囦欢宸插瓨鍦紝璺宠繃
)

REM 鍒涘缓鐩綍
echo.
echo [3/6] 鍒涘缓鏈湴瀛樺偍鐩綍...
if not exist "experiences" mkdir experiences
if not exist "cache" mkdir cache
if not exist "cache\experiences" mkdir cache\experiences
if not exist "logs" mkdir logs
echo [OK] 鐩綍鍒涘缓瀹屾垚

REM 娴嬭瘯 MinIO 杩炴帴
echo.
echo [4/6] 娴嬭瘯 MinIO 杩炴帴...
python -c "from src.core.minio_client import MinIOClient; c = MinIOClient(); c.test_connection()" >nul 2>&1
if errorlevel 1 (
    echo [璀﹀憡] MinIO 杩炴帴澶辫触
    echo 璇锋鏌?
    echo   1. 缃戠粶鏄惁鍙揪 218.201.18.133:8010
    echo   2. 瀹夊叏缁勬槸鍚﹀紑鏀?8010 绔彛
) else (
    echo [OK] MinIO 杩炴帴鎴愬姛
)

REM 鍒濆鍖栨暟鎹簱琛?echo.
echo [5/6] 娴嬭瘯鏁版嵁搴撹繛鎺?..
python src\cli\memory_cli.py status >nul 2>&1
if errorlevel 1 (
    echo [璀﹀憡] 鏁版嵁搴撹繛鎺ュけ璐?    echo 璇锋鏌?
    echo   1. 缃戠粶鏄惁鍙揪 218.201.18.133:8999
    echo   2. 鏁版嵁搴撳瘑鐮佹槸鍚︽纭?) else (
    echo [OK] 鏁版嵁搴撹繛鎺ユ垚鍔?)

REM 娴嬭瘯瀛樺偍鍔熻兘
echo.
echo [6/6] 娴嬭瘯瀛樺偍鍔熻兘...
echo [娴嬭瘯] 杩欐槸涓€鏉℃祴璇曡蹇?> nul
python src\cli\memory_cli.py store "鏈湴娴嬭瘯璁板繂" --type general --tags test >nul 2>&1
if errorlevel 1 (
    echo [璀﹀憡] 瀛樺偍娴嬭瘯澶辫触
) else (
    echo [OK] 瀛樺偍鍔熻兘姝ｅ父
)

echo.
echo ========================================
echo   瀹夎瀹屾垚锛?echo ========================================
echo.
echo 甯哥敤鍛戒护:
echo.
echo   鏌ョ湅鐘舵€?       python src\cli\memory_cli.py status
echo   瀛樺偍璁板繂:      python src\cli\memory_cli.py store "鍐呭"
echo   鍒嗕韩缁忛獙:      python src\cli\memory_cli.py exp-create --help
echo   鏌ヨ浜戠:      python src\cli\memory_cli.py cloud-query "鍏抽敭璇?
echo   鍒楀嚭缁忛獙:      python src\cli\memory_cli.py exp-list
echo   MinIO 娴嬭瘯:    python src\core\minio_client.py test
echo.
echo 璇︾粏鏂囨。: README.md
echo 蹇€熶笂鎵? QUICKSTART.md
echo.
pause

