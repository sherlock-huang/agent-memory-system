#!/bin/bash
# ============================================
# Agent Memory System - 一键安装脚本 (Linux/macOS)
# ============================================
#
# 用法:
#   curl -fsSL https://xxx/install.sh | bash
#   或下载后直接运行: bash install.sh
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================"
echo "  Agent Memory System - 一键安装"
echo "========================================"

# 检测操作系统
OS=$(uname -s)
print_info "检测操作系统: $OS"

# 创建配置目录
CONFIG_DIR="$HOME/.memory"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$CONFIG_DIR"
mkdir -p "$BIN_DIR"

# 选择存储方案
echo ""
echo "请选择存储方案:"
echo "  1) MySQL (需要云端数据库)"
echo "  2) SQLite (本地/云服务器文件共享)"
echo "  3) 自动检测并配置"
echo ""
read -p "请选择 [1/2/3] (默认 3): " choice
choice=${choice:-3}

case $choice in
    1)
        print_info "选择 MySQL 存储方案"
        echo ""
        read -p "  MySQL Host: " MYSQL_HOST
        read -p "  MySQL Port [3306]: " MYSQL_PORT
        read -p "  Database [agent_memory]: " MYSQL_DB
        read -p "  Username: " MYSQL_USER
        read -s -p "  Password: " MYSQL_PASS
        echo ""
        
        # 生成配置
        cat > "$CONFIG_DIR/config.yaml" << EOF
database:
  type: mysql
  host: "$MYSQL_HOST"
  port: ${MYSQL_PORT:-3306}
  database: ${MYSQL_DB:-agent_memory}
  user: "$MYSQL_USER"
  password: "$MYSQL_PASS"
  charset: "utf8mb4"
  pool:
    min_size: 5
    max_size: 20

source: "cli"
agent_id: null
EOF
        ;;
    2)
        print_info "选择 SQLite 存储方案"
        
        # 检测网络路径
        echo ""
        echo "SQLite 文件将存储在: $CONFIG_DIR/memory.db"
        echo "如需多机共享，请设置网络共享路径 (SMB/NFS)"
        echo ""
        read -p "是否设置网络共享路径? [y/N]: " use_network
        use_network=${use_network:-n}
        
        if [[ "$use_network" =~ ^[Yy]$ ]]; then
            read -p "  网络路径 (如 //server/share/memory.db): " DB_PATH
        else
            DB_PATH="$CONFIG_DIR/memory.db"
        fi
        
        # 生成配置
        cat > "$CONFIG_DIR/config.yaml" << EOF
database:
  type: sqlite
  path: "$DB_PATH"

source: "cli"
agent_id: null
EOF
        ;;
    3|"")
        print_info "自动检测存储方案..."
        
        # 检测 MySQL
        if command -v mysql &> /dev/null; then
            print_info "检测到 mysql 命令"
        fi
        
        # 默认 SQLite
        print_info "使用 SQLite 本地存储"
        
        cat > "$CONFIG_DIR/config.yaml" << EOF
database:
  type: sqlite
  path: "$CONFIG_DIR/memory.db"

source: "cli"
agent_id: null
EOF
        ;;
esac

# 安装 Python CLI
print_info "安装 Memory CLI..."

CLI_PATH="$BIN_DIR/memory"

# 尝试下载
if command -v curl &> /dev/null; then
    curl -fsSL -o "$CLI_PATH" "https://xxx/memory.py" 2>/dev/null || {
        print_warn "无法下载，将使用本地源码"
        # 复制本地源码
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        if [ -f "$SCRIPT_DIR/src/cli/memory_cli.py" ]; then
            cp "$SCRIPT_DIR/src/cli/memory_cli.py" "$CLI_PATH"
        fi
    }
elif command -v wget &> /dev/null; then
    wget -q -O "$CLI_PATH" "https://xxx/memory.py" 2>/dev/null || {
        print_warn "无法下载，将使用本地源码"
    }
else
    print_warn "curl/wget 均不可用，使用本地源码"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -f "$SCRIPT_DIR/src/cli/memory_cli.py" ]; then
        cp "$SCRIPT_DIR/src/cli/memory_cli.py" "$CLI_PATH"
    fi
fi

chmod +x "$CLI_PATH" 2>/dev/null || true

# 安装依赖
print_info "安装 Python 依赖..."

if command -v pip3 &> /dev/null; then
    pip3 install pymysql dbutils pyyaml 2>/dev/null || print_warn "依赖安装失败，请手动安装: pip3 install pymysql dbutils pyyaml"
elif command -v pip &> /dev/null; then
    pip install pymysql dbutils pyyaml 2>/dev/null || print_warn "依赖安装失败"
fi

# 初始化数据库
print_info "初始化数据库..."

if command -v python3 &> /dev/null; then
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/src')
from core import init_config, init_db
try:
    init_config()
    init_db()
    print('[OK] 数据库初始化成功')
except Exception as e:
    print(f'[WARN] 数据库初始化: {e}')
" 2>/dev/null || print_warn "数据库初始化失败，请稍后手动运行 memory status"
elif command -v python &> /dev/null; then
    python -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/src')
from core import init_config, init_db
try:
    init_config()
    init_db()
    print('[OK] 数据库初始化成功')
except Exception as e:
    print(f'[WARN] 数据库初始化: {e}')
" 2>/dev/null || print_warn "数据库初始化失败"
fi

# 添加到 PATH
echo ""
echo "添加到 PATH (如果需要)..."
if [ -f "$HOME/.bashrc" ]; then
    if ! grep -q ".local/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        print_info "已添加 ~/.local/bin 到 PATH (bash)"
    fi
fi

if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q ".local/bin" "$HOME/.zshrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        print_info "已添加 ~/.local/bin 到 PATH (zsh)"
    fi
fi

# 完成
echo ""
echo "========================================"
echo "  安装完成!"
echo "========================================"
print_info "配置位置: $CONFIG_DIR/config.yaml"
print_info "CLI 位置: $CLI_PATH"
echo ""
echo "快速开始:"
echo "  memory status        # 查看状态"
echo "  memory store '内容'  # 存储记忆"
echo "  memory search '查询' # 搜索记忆"
echo "  memory --help       # 查看帮助"
echo ""
```

## PowerShell 安装脚本 (Windows)
```powershell
# install.ps1 - Agent Memory System 一键安装 (Windows)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agent Memory System - 安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 创建配置目录
$ConfigDir = "$env:LOCALAPPDATA\.memory"
$BinDir = "$env:LOCALAPPDATA\.memory"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# 选择存储方案
Write-Host ""
Write-Host "请选择存储方案:" -ForegroundColor Yellow
Write-Host "  1) MySQL (需要云端数据库)"
Write-Host "  2) SQLite (本地存储)"
$choice = Read-Host "请选择 [1/2] (默认 2)"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "MySQL 连接信息:" -ForegroundColor Green
    $host = Read-Host "  Host"
    $port = Read-Host "  Port" -Default "3306"
    $db = Read-Host "  Database" -Default "agent_memory"
    $user = Read-Host "  Username"
    $pass = Read-Host "  Password" -AsSecureString
    
    $config = @"
database:
  type: mysql
  host: "$host"
  port: $port
  database: "$db"
  user: "$user"
  password: "$($pass | ConvertFrom-SecureString -AsPlainText)"
  charset: "utf8mb4"
  pool:
    min_size: 5
    max_size: 20

source: "cli"
agent_id: null
"@
} else {
    $dbPath = "$ConfigDir\memory.db"
    Write-Host ""
    Write-Host "SQLite 数据库将存储在: $dbPath" -ForegroundColor Green
    
    $config = @"
database:
  type: sqlite
  path: "$dbPath"

source: "cli"
agent_id: null
"@
}

# 保存配置
$config | Out-File -FilePath "$ConfigDir\config.yaml" -Encoding UTF8

# 下载/复制 CLI
Write-Host ""
Write-Host "安装 Memory CLI..." -ForegroundColor Green
$cliPath = "$BinDir\memory.exe"

# 尝试下载
try {
    Invoke-WebRequest -Uri "https://xxx/memory.exe" -OutFile $cliPath -UseBasicParsing -ErrorAction SilentlyContinue
    if (Test-Path $cliPath) {
        Write-Host "[OK] CLI 下载成功" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] 下载失败，复制本地源码..." -ForegroundColor Yellow
    $srcPath = "$PSScriptRoot\src\cli\memory_cli.py"
    if (Test-Path $srcPath) {
        Copy-Item $srcPath "$BinDir\memory.py" -Force
        Write-Host "[OK] CLI 复制成功" -ForegroundColor Green
    }
}

# 安装 Python 依赖
Write-Host ""
Write-Host "检查 Python 依赖..." -ForegroundColor Green
$pythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}

if ($pythonCmd) {
    Write-Host "使用: $pythonCmd" -ForegroundColor Cyan
    & $pythonCmd -m pip install pymysql dbutils pyyaml -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] 依赖安装成功" -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] 未找到 Python，请手动安装依赖: pip install pymysql dbutils pyyaml" -ForegroundColor Yellow
}

# 初始化数据库
Write-Host ""
Write-Host "初始化数据库..." -ForegroundColor Green
$cliFullPath = if (Test-Path "$BinDir\memory.exe") { "$BinDir\memory.exe" } else { "$BinDir\memory.py" }
& python $cliFullPath status 2>$null | Out-String -Stream | ForEach-Object { Write-Host $_ }

# 完成
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "配置: $ConfigDir\config.yaml"
Write-Host "CLI: $cliFullPath"
Write-Host ""
Write-Host "快速开始:"
Write-Host '  memory status        # 查看状态'
Write-Host '  memory store "内容"  # 存储记忆'
Write-Host '  memory search "查询" # 搜索记忆'
Write-Host '  memory --help       # 查看帮助'
```
