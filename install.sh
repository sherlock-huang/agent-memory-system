#!/bin/bash
# ============================================
#  Agent Memory System - Linux/macOS 安装脚本
# ============================================
#
# 使用方法:
#   1. chmod +x install.sh
#   2. ./install.sh
#

set -e

echo ""
echo "========================================"
echo "  Agent Memory System 安装向导"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3"
    echo "请先安装 Python 3.8+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi
echo "[OK] Python3 已找到: $(python3 --version)"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "[错误] 未找到 pip3"
    echo "请运行: sudo apt install python3-pip"
    exit 1
fi
echo "[OK] pip3 已找到"

# 安装依赖
echo ""
echo "[1/6] 安装 Python 依赖..."
pip3 install pyyaml mysql-connector-python boto3 --quiet
echo "[OK] 依赖安装完成"

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查项目文件
if [ ! -f "src/cli/memory_cli.py" ]; then
    echo "[错误] 找不到 memory_cli.py"
    echo "请确保此脚本在 agent-memory-system 目录下运行"
    exit 1
fi
echo "[OK] 项目文件已找到: $SCRIPT_DIR"

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "[2/6] 创建配置文件..."
    cat > config.yaml << 'EOF'
# Agent Memory System - Configuration

# MinIO 云端存储
minio:
  endpoint: "218.201.18.133:9002"
  access_key: "admin"
  secret_key: "Minio12345678"
  bucket: "openclaw"
  region: "cn-east-1"
  cache_dir: "./cache/experiences"

# MySQL 数据库
database:
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
    echo "[OK] 配置文件已创建"
else
    echo "[2/6] 配置文件已存在，跳过"
fi

# 创建目录
echo ""
echo "[3/6] 创建本地存储目录..."
mkdir -p experiences cache/experiences logs
echo "[OK] 目录创建完成"

# 测试 MinIO 连接
echo ""
echo "[4/6] 测试 MinIO 连接..."
if python3 -c "from src.core.minio_client import MinIOClient; c = MinIOClient(); c.test_connection()" 2>/dev/null; then
    echo "[OK] MinIO 连接成功"
else
    echo "[警告] MinIO 连接失败"
    echo "请检查:"
    echo "  1. 网络是否可达 218.201.18.133:9002"
    echo "  2. 安全组是否开放 9002 端口"
fi

# 测试数据库连接
echo ""
echo "[5/6] 测试数据库连接..."
if python3 src/cli/memory_cli.py status > /dev/null 2>&1; then
    echo "[OK] 数据库连接成功"
else
    echo "[警告] 数据库连接失败"
    echo "请检查:"
    echo "  1. 网络是否可达 218.201.18.133:8999"
    echo "  2. 数据库密码是否正确"
fi

# 测试存储功能
echo ""
echo "[6/6] 测试存储功能..."
if echo "测试记忆" | python3 src/cli/memory_cli.py store "本地测试记忆" --type general --tags test > /dev/null 2>&1; then
    echo "[OK] 存储功能正常"
else
    echo "[警告] 存储测试失败"
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "常用命令:"
echo ""
echo "  查看状态:       python3 src/cli/memory_cli.py status"
echo "  存储记忆:       python3 src/cli/memory_cli.py store \"内容\""
echo "  分享经验:       python3 src/cli/memory_cli.py exp-create --help"
echo "  查询云端:       python3 src/cli/memory_cli.py cloud-query \"关键词\""
echo "  列出经验:       python3 src/cli/memory_cli.py exp-list"
echo "  MinIO 测试:     python3 src/core/minio_client.py test"
echo ""
echo "详细文档: README.md"
echo "快速上手: QUICKSTART.md"
echo ""
