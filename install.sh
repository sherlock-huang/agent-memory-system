#!/bin/bash
# ============================================
#  Agent Memory System - Linux/macOS 瀹夎鑴氭湰
# ============================================
#
# 浣跨敤鏂规硶:
#   1. chmod +x install.sh
#   2. ./install.sh
#

set -e

echo ""
echo "========================================"
echo "  Agent Memory System 瀹夎鍚戝"
echo "========================================"
echo ""

# 妫€鏌?Python
if ! command -v python3 &> /dev/null; then
    echo "[閿欒] 鏈壘鍒?Python3"
    echo "璇峰厛瀹夎 Python 3.8+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi
echo "[OK] Python3 宸叉壘鍒? $(python3 --version)"

# 妫€鏌?pip
if ! command -v pip3 &> /dev/null; then
    echo "[閿欒] 鏈壘鍒?pip3"
    echo "璇疯繍琛? sudo apt install python3-pip"
    exit 1
fi
echo "[OK] pip3 宸叉壘鍒?

# 瀹夎渚濊禆
echo ""
echo "[1/6] 瀹夎 Python 渚濊禆..."
pip3 install pyyaml mysql-connector-python boto3 --quiet
echo "[OK] 渚濊禆瀹夎瀹屾垚"

# 鑾峰彇鑴氭湰鐩綍
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 妫€鏌ラ」鐩枃浠?if [ ! -f "src/cli/memory_cli.py" ]; then
    echo "[閿欒] 鎵句笉鍒?memory_cli.py"
    echo "璇风‘淇濇鑴氭湰鍦?agent-memory-system 鐩綍涓嬭繍琛?
    exit 1
fi
echo "[OK] 椤圭洰鏂囦欢宸叉壘鍒? $SCRIPT_DIR"

# 妫€鏌ラ厤缃枃浠?if [ ! -f "config.yaml" ]; then
    echo ""
    echo "[2/6] 鍒涘缓閰嶇疆鏂囦欢..."
    cat > config.yaml << 'EOF'
# Agent Memory System - Configuration

# MinIO 浜戠瀛樺偍
minio:
  endpoint: "218.201.18.133:8010"
  access_key: "admin"
  secret_key: "Minio12345678"
  bucket: "openclaw"
  region: "cn-east-1"
  cache_dir: "./cache/experiences"

# MySQL 鏁版嵁搴?database:
  type: mysql
  host: "218.201.18.133"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "${MEMORY_DB_PASSWORD:-lJ0^)sG0\\dI1~gN1\"lJ6|}"
  charset: "utf8mb4"

source: "cli"
agent_id: null

search:
  default_limit: 10
  max_limit: 100

log_level: "INFO"
EOF
    echo "[OK] 閰嶇疆鏂囦欢宸插垱寤?
else
    echo "[2/6] 閰嶇疆鏂囦欢宸插瓨鍦紝璺宠繃"
fi

# 鍒涘缓鐩綍
echo ""
echo "[3/6] 鍒涘缓鏈湴瀛樺偍鐩綍..."
mkdir -p experiences cache/experiences logs
echo "[OK] 鐩綍鍒涘缓瀹屾垚"

# 娴嬭瘯 MinIO 杩炴帴
echo ""
echo "[4/6] 娴嬭瘯 MinIO 杩炴帴..."
if python3 -c "from src.core.minio_client import MinIOClient; c = MinIOClient(); c.test_connection()" 2>/dev/null; then
    echo "[OK] MinIO 杩炴帴鎴愬姛"
else
    echo "[璀﹀憡] MinIO 杩炴帴澶辫触"
    echo "璇锋鏌?"
    echo "  1. 缃戠粶鏄惁鍙揪 218.201.18.133:8010"
    echo "  2. 瀹夊叏缁勬槸鍚﹀紑鏀?8010 绔彛"
fi

# 娴嬭瘯鏁版嵁搴撹繛鎺?echo ""
echo "[5/6] 娴嬭瘯鏁版嵁搴撹繛鎺?.."
if python3 src/cli/memory_cli.py status > /dev/null 2>&1; then
    echo "[OK] 鏁版嵁搴撹繛鎺ユ垚鍔?
else
    echo "[璀﹀憡] 鏁版嵁搴撹繛鎺ュけ璐?
    echo "璇锋鏌?"
    echo "  1. 缃戠粶鏄惁鍙揪 218.201.18.133:8999"
    echo "  2. 鏁版嵁搴撳瘑鐮佹槸鍚︽纭?
fi

# 娴嬭瘯瀛樺偍鍔熻兘
echo ""
echo "[6/6] 娴嬭瘯瀛樺偍鍔熻兘..."
if echo "娴嬭瘯璁板繂" | python3 src/cli/memory_cli.py store "鏈湴娴嬭瘯璁板繂" --type general --tags test > /dev/null 2>&1; then
    echo "[OK] 瀛樺偍鍔熻兘姝ｅ父"
else
    echo "[璀﹀憡] 瀛樺偍娴嬭瘯澶辫触"
fi

echo ""
echo "========================================"
echo "  瀹夎瀹屾垚锛?
echo "========================================"
echo ""
echo "甯哥敤鍛戒护:"
echo ""
echo "  鏌ョ湅鐘舵€?       python3 src/cli/memory_cli.py status"
echo "  瀛樺偍璁板繂:       python3 src/cli/memory_cli.py store \"鍐呭\""
echo "  鍒嗕韩缁忛獙:       python3 src/cli/memory_cli.py exp-create --help"
echo "  鏌ヨ浜戠:       python3 src/cli/memory_cli.py cloud-query \"鍏抽敭璇峔""
echo "  鍒楀嚭缁忛獙:       python3 src/cli/memory_cli.py exp-list"
echo "  MinIO 娴嬭瘯:     python3 src/core/minio_client.py test"
echo ""
echo "璇︾粏鏂囨。: README.md"
echo "蹇€熶笂鎵? QUICKSTART.md"
echo ""

