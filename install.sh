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
    echo "请先安装 Python 3.8+"
    exit 1
fi
echo "[OK] Python3 已找到: $(python3 --version)"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "[错误] 未找到 pip3"
    echo "请运行: sudo apt install python3-pip 或 brew install python3"
    exit 1
fi
echo "[OK] pip3 已找到"

# 安装依赖
echo ""
echo "[1/4] 安装 Python 依赖..."
pip3 install pyyaml mysql-connector-python --quiet
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

# 设置数据库密码
echo ""
echo "[2/4] 配置数据库连接"
echo ""
read -p "请输入数据库密码 (直接回车使用默认密码): " DB_PASS

if [ -z "$DB_PASS" ]; then
    DB_PASS='lJ0)sG0\dI1~gN1"lJ6|'
    echo "使用默认密码"
fi

# 更新配置文件
echo "[3/4] 更新配置文件..."
cat > config.yaml << EOF
# Agent Memory System - Configuration

database:
  type: mysql
  host: "218.201.18.131"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "${DB_PASS}"
  charset: "utf8mb4"

source: "cli"
agent_id: null

search:
  default_limit: 10
  max_limit: 100

log_level: "INFO"
EOF

echo "[OK] 配置文件已生成"

# 测试连接
echo ""
echo "[4/4] 测试数据库连接..."
if python3 src/cli/memory_cli.py status > /dev/null 2>&1; then
    echo "[OK] 数据库连接成功"
else
    echo ""
    echo "[警告] 数据库连接失败"
    echo "请检查:"
    echo "  1. 密码是否正确"
    echo "  2. 网络是否可达 218.201.18.131:8999"
    echo ""
    echo "配置文件已生成，可以稍后手动测试"
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "常用命令:"
echo ""
echo "  查看状态:   python3 src/cli/memory_cli.py status"
echo "  存储记忆:   python3 src/cli/memory_cli.py store \"内容\""
echo "  分享经验:   python3 src/cli/memory_cli.py share-experience --help"
echo "  查询云端:   python3 src/cli/memory_cli.py cloud-query \"关键词\""
echo ""
echo "详细文档: README.md"
echo ""
