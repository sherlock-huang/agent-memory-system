# Agent Memory System - 架构方案 (云端版)

**版本:** v3.0  
**日期:** 2026-04-07  
**存储:** MySQL 5.7+ / MySQL 8.0+ / SQLite (云端)

---

## 1. 存储方案选择

```
┌─────────────────────────────────────────────────────────────────┐
│                    存储方案选择                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   方案 A: MySQL (云端)                                          │
│   ├── MySQL 5.7 (广泛兼容)                                      │
│   └── MySQL 8.0+ (完整功能)                                     │
│                                                                  │
│   方案 B: SQLite (云服务器文件共享)                              │
│   └── 适合小团队 / 不想用 MySQL 的用户                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 方案对比

| 特性 | MySQL 5.7 | MySQL 8.0+ | SQLite (云端) |
|------|------------|-------------|----------------|
| **兼容性** | 广泛 | 新版 | 通用 |
| **JSON 支持** | TEXT 存储 | 原生 JSON | TEXT |
| **全文搜索** | 有限 | FULLTEXT+ | FTS5 |
| **向量支持** | 无 | 原生向量 | 扩展 |
| **连接方式** | TCP/IP | TCP/IP | 文件共享 |
| **并发** | 高 | 高 | 一般 |
| **安装难度** | 需云服务 | 需云服务 | ⭐ 最简单 |

---

## 2. 统一架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Memory System                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Storage Abstraction Layer                      │   │
│  │                      (存储抽象层，统一接口)                          │   │
│  │                                                                  │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│  │   │  MySQL 5.7 │  │  MySQL 8.0+ │  │    SQLite  │           │   │
│  │   │  Adapter   │  │   Adapter  │  │   Adapter  │           │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘           │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Core Engine (核心引擎)                         │   │
│  │   StoreEngine + SearchEngine + ACLEngine                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Interface Layer                                │   │
│  │   CLI + REST API + SDK                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. MySQL 5.7 Schema (兼容版)

```sql
-- ============================================
-- Agent Memory System - MySQL 5.7/8.0 通用 Schema
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS agent_memory
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agent_memory;

-- ============================================
-- 1. 共享记忆表 (MySQL 5.7 兼容)
-- ============================================
CREATE TABLE IF NOT EXISTS memories (
    id VARCHAR(50) PRIMARY KEY COMMENT '记忆ID',
    content TEXT NOT NULL COMMENT '记忆内容',
    summary VARCHAR(500) COMMENT '摘要',
    
    -- 分类
    type ENUM('general', 'project', 'preference', 'knowledge', 'team') 
        NOT NULL DEFAULT 'general',
    visibility ENUM('private', 'shared', 'global') 
        NOT NULL DEFAULT 'shared',
    
    -- 来源
    source ENUM('cli', 'openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL DEFAULT 'cli',
    source_agent VARCHAR(100),
    project_path VARCHAR(500),
    
    -- 评分
    importance DECIMAL(3,1) DEFAULT 5.0,
    
    -- 标签 (5.7 用 VARCHAR(1000) 存储 JSON 字符串)
    tags VARCHAR(1000) DEFAULT '{}',
    
    -- 时间戳
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- 状态
    is_deleted TINYINT(1) DEFAULT 0,
    
    -- 索引
    INDEX idx_type (type),
    INDEX idx_visibility (visibility),
    INDEX idx_project (project_path(255)),
    INDEX idx_source (source),
    INDEX idx_created (created_at DESC),
    INDEX idx_deleted (is_deleted),
    INDEX idx_importance (importance)
    
    -- MySQL 5.7 不支持 FULLTEXT 在 TEXT 列上，先用普通索引
    -- 如需全文搜索，可用 LIKE 查询
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. Agent 注册表
-- ============================================
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(100) PRIMARY KEY,
    type ENUM('openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL,
    name VARCHAR(100),
    description VARCHAR(500),
    api_key_hash VARCHAR(255),
    version VARCHAR(50),
    capabilities VARCHAR(1000) DEFAULT '{}',
    status ENUM('active', 'inactive', 'disconnected') DEFAULT 'active',
    registered_at BIGINT NOT NULL,
    last_seen BIGINT,
    
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. 访问控制表
-- ============================================
CREATE TABLE IF NOT EXISTS acl (
    memory_id VARCHAR(50) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    permission ENUM('read', 'write', 'admin') NOT NULL DEFAULT 'read',
    grant_type ENUM('direct', 'inherited', 'role') DEFAULT 'direct',
    granted_by VARCHAR(100) NOT NULL,
    granted_at BIGINT NOT NULL,
    expires_at BIGINT,
    
    PRIMARY KEY (memory_id, agent_id),
    INDEX idx_agent (agent_id),
    INDEX idx_expires (expires_at),
    
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. 向量缓存表
-- ============================================
CREATE TABLE IF NOT EXISTS embeddings (
    content_hash VARCHAR(64) PRIMARY KEY,
    embedding LONGBLOB,
    model VARCHAR(50),
    dimension INT,
    created_at BIGINT,
    
    INDEX idx_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. 搜索历史表
-- ============================================
CREATE TABLE IF NOT EXISTS search_history (
    id VARCHAR(50) PRIMARY KEY,
    query TEXT NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    results_count INT DEFAULT 0,
    results_ids VARCHAR(2000) DEFAULT '[]',
    latency_ms INT,
    searched_at BIGINT NOT NULL,
    
    INDEX idx_agent (agent_id),
    INDEX idx_session (session_id),
    INDEX idx_searched (searched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. 访问日志表
-- ============================================
CREATE TABLE IF NOT EXISTS access_log (
    id VARCHAR(50) PRIMARY KEY,
    memory_id VARCHAR(50),
    agent_id VARCHAR(100) NOT NULL,
    action ENUM('read', 'write', 'delete', 'share', 'grant', 'revoke') NOT NULL,
    details VARCHAR(1000) DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    accessed_at BIGINT NOT NULL,
    
    INDEX idx_agent (agent_id),
    INDEX idx_memory (memory_id),
    INDEX idx_action (action),
    INDEX idx_accessed (accessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 7. 角色表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_roles (
    id VARCHAR(50) PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    role_type ENUM('owner', 'admin', 'member', 'guest') DEFAULT 'member',
    project_path VARCHAR(500),
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    UNIQUE KEY uk_agent_project (agent_id, project_path),
    INDEX idx_role_type (role_type),
    
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 4. SQLite Schema (云端共享方案)

```sql
-- ============================================
-- Agent Memory System - SQLite Schema
-- 用于云服务器文件共享
-- ============================================

-- 共享记忆表
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    summary TEXT,
    type TEXT NOT NULL DEFAULT 'general',
    visibility TEXT NOT NULL DEFAULT 'shared',
    source TEXT NOT NULL DEFAULT 'cli',
    source_agent TEXT,
    project_path TEXT,
    importance REAL DEFAULT 5.0,
    tags TEXT DEFAULT '[]',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    is_deleted INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_visibility ON memories(visibility);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_path);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(is_deleted);

-- Agent 表
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT,
    description TEXT,
    api_key_hash TEXT,
    version TEXT,
    capabilities TEXT DEFAULT '{}',
    status TEXT DEFAULT 'active',
    registered_at INTEGER NOT NULL,
    last_seen INTEGER
);

CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- ACL 表
CREATE TABLE IF NOT EXISTS acl (
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'read',
    granted_by TEXT NOT NULL,
    granted_at INTEGER NOT NULL,
    expires_at INTEGER,
    PRIMARY KEY (memory_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_acl_agent ON acl(agent_id);

-- 向量缓存
CREATE TABLE IF NOT EXISTS embeddings (
    content_hash TEXT PRIMARY KEY,
    embedding BLOB,
    model TEXT,
    dimension INTEGER,
    created_at INTEGER
);

-- 搜索历史
CREATE TABLE IF NOT EXISTS search_history (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    results_count INTEGER DEFAULT 0,
    results_ids TEXT DEFAULT '[]',
    latency_ms INTEGER,
    searched_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_history_agent ON search_history(agent_id);

-- 角色表
CREATE TABLE IF NOT EXISTS agent_roles (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    role_type TEXT DEFAULT 'member',
    project_path TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(agent_id, project_path)
);
```

---

## 5. 存储适配器设计

```python
# src/core/storage_adapter.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import json


class StorageAdapter(ABC):
    """存储适配器基类"""
    
    @abstractmethod
    def insert_memory(self, memory) -> memory:
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[memory]:
        pass
    
    @abstractmethod
    def search_memories(self, query: str, **kwargs) -> List[Tuple[memory, float]]:
        pass
    
    @abstractmethod
    def list_memories(self, **kwargs) -> List[memory]:
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str, hard: bool = False) -> bool:
        pass


class MySQL57Adapter(StorageAdapter):
    """MySQL 5.7 适配器"""
    
    def __init__(self, config: dict):
        import pymysql
        from dbutils.pooled_db import PooledDB
        
        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=20,
            mincached=5,
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        # JSON 存储为 VARCHAR
        self.json_columns = ['tags', 'capabilities', 'results_ids', 'details']
    
    def _serialize_json(self, obj) -> str:
        if obj is None:
            return '{}'
        if isinstance(obj, (dict, list)):
            return json.dumps(obj, ensure_ascii=False)
        return str(obj)
    
    def _deserialize_json(self, text: str) -> Any:
        if not text:
            return {} if '}' in text else []
        try:
            return json.loads(text)
        except:
            return {}


class MySQL80Adapter(StorageAdapter):
    """MySQL 8.0+ 适配器"""
    
    def __init__(self, config: dict):
        import pymysql
        from dbutils.pooled_db import PooledDB
        
        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=20,
            mincached=5,
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        # MySQL 8.0 支持原生 JSON
        self.json_columns = []
    
    def _json_column(self, col: str) -> str:
        # MySQL 8.0 直接用 JSON 函数
        return f"JSON_EXTRACT({col}, '$')"


class SQLiteAdapter(StorageAdapter):
    """SQLite 适配器 (云端文件共享)"""
    
    def __init__(self, db_path: str):
        import sqlite3
        
        # 支持网络路径 (SMB/NFS)
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30.0
        )
        self.conn.row_factory = sqlite3.Row
        
        # WAL 模式提升并发
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
```

---

## 6. 自动检测与选择

```python
# src/core/database_manager.py

def create_storage(config: dict) -> StorageAdapter:
    """
    根据配置自动创建合适的存储适配器
    
    优先级:
    1. MySQL 8.0 (完整功能)
    2. MySQL 5.7 (兼容模式)
    3. SQLite (最简单)
    """
    
    if config.get('type') == 'mysql':
        # 检测 MySQL 版本
        version = detect_mysql_version(config)
        
        if version >= 8.0:
            return MySQL80Adapter(config)
        else:
            return MySQL57Adapter(config)
    
    elif config.get('type') == 'sqlite':
        return SQLiteAdapter(config['path'])
    
    else:
        raise ValueError(f"Unknown storage type: {config.get('type')}")


def detect_mysql_version(config: dict) -> float:
    """检测 MySQL 版本"""
    import pymysql
    
    conn = pymysql.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password']
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version_str = cursor.fetchone()[0]
    conn.close()
    
    # 提取主版本号
    version = float(version_str.split('.')[0])
    return version
```

---

## 7. 一键安装脚本

```bash
#!/bin/bash
# install.sh - 一键安装脚本 (Linux/macOS)

set -e

echo "========================================"
echo "  Agent Memory System - 一键安装"
echo "========================================"

# 检测操作系统
OS=$(uname -s)

# 创建配置目录
mkdir -p ~/.memory

# 选择存储方案
echo ""
echo "请选择存储方案:"
echo "1) MySQL (需要云端数据库)"
echo "2) SQLite (云服务器文件共享，本地部署)"
echo "3) 自动检测"

read -p "请选择 [1/2/3]: " choice

case $choice in
    1)
        echo "请提供 MySQL 连接信息:"
        read -p "  Host: " MYSQL_HOST
        read -p "  Port [3306]: " MYSQL_PORT
        read -p "  Database [agent_memory]: " MYSQL_DB
        read -p "  Username: " MYSQL_USER
        read -s -p "  Password: " MYSQL_PASS
        echo ""
        
        # 生成配置
        cat > ~/.memory/config.yaml << EOF
database:
  type: mysql
  host: "$MYSQL_HOST"
  port: ${MYSQL_PORT:-3306}
  database: ${MYSQL_DB:-agent_memory}
  user: "$MYSQL_USER"
  password: "$MYSQL_PASS"
EOF
        ;;
    2)
        # SQLite 配置
        cat > ~/.memory/config.yaml << EOF
database:
  type: sqlite
  path: ~/.memory/memory.db
EOF
        ;;
    3)
        # 自动检测
        echo "检测中..."
        # 自动检测逻辑
        ;;
esac

# 下载 CLI
echo ""
echo "下载 Memory CLI..."
curl -fsSL https://raw.githubusercontent.com/xxx/memory -o ~/.local/bin/memory
chmod +x ~/.local/bin/memory

echo ""
echo "验证安装..."
memory status

echo ""
echo "========================================"
echo "  安装完成!"
echo "========================================"
echo "使用 memory --help 查看命令"
```

---

## 8. Windows 一键安装 (PowerShell)

```powershell
# install.ps1 - Windows 一键安装

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agent Memory System - 安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 创建配置目录
$ConfigDir = "$env:LOCALAPPDATA\.memory"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# 选择存储方案
Write-Host ""
Write-Host "请选择存储方案:" -ForegroundColor Yellow
Write-Host "1) MySQL (需要云端数据库)"
Write-Host "2) SQLite (云服务器文件共享)"
$choice = Read-Host "请选择 [1/2]"

if ($choice -eq "1") {
    $host = Read-Host "MySQL Host"
    $port = Read-Host "MySQL Port" -Default "3306"
    $db = Read-Host "Database" -Default "agent_memory"
    $user = Read-Host "Username"
    $pass = Read-Host "Password" -AsSecureString
    
    $config = @"
database:
  type: mysql
  host: "$host"
  port: $port
  database: "$db"
  user: "$user"
  password: "$($pass | ConvertFrom-SecureString -AsPlainText)"
"@
} else {
    $config = @"
database:
  type: sqlite
  path: "$ConfigDir\memory.db"
"@
}

# 保存配置
$config | Out-File -FilePath "$ConfigDir\config.yaml" -Encoding UTF8

# 下载 CLI
Write-Host "下载 Memory CLI..." -ForegroundColor Green
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/xxx/memory" -OutFile "$ConfigDir\memory.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "运行: $ConfigDir\memory.exe status"
```

---

## 9. 技术差异总结

| 功能 | MySQL 5.7 | MySQL 8.0+ | SQLite |
|------|-----------|------------|--------|
| JSON 存储 | VARCHAR | 原生 JSON | TEXT |
| 全文搜索 | LIKE | FULLTEXT | FTS5 |
| 向量搜索 | 外部服务 | 原生/外部 | 外部服务 |
| 窗口函数 | ❌ | ✅ | ✅ |
| CTEs | ❌ | ✅ | ✅ |
| 字符集 | utf8mb3 | utf8mb4 | UTF-8 |

---

## 10. 配置示例

### MySQL 5.7
```yaml
database:
  type: mysql
  host: "218.201.18.131"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "your-password"
  charset: "utf8mb4"
```

### MySQL 8.0+
```yaml
database:
  type: mysql
  host: "your-mysql8-host.com"
  port: 3306
  database: "agent_memory"
  user: "memory_user"
  password: "your-password"
  charset: "utf8mb4"
  version: 8.0  # 指定版本
```

### SQLite (云端)
```yaml
database:
  type: sqlite
  path: "/shared/memory/memory.db"  # 共享网络路径
```

---

*架构设计 v3.0 - 支持 MySQL 5.7/8.0+ 和 SQLite*
