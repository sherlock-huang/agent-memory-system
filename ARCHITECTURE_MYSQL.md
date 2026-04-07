# Agent Memory System - 架构方案 (MySQL 云端版)

**版本:** v2.0  
**日期:** 2026-04-07  
**存储:** 云端 MySQL

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Memory System                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      MySQL Cloud Database                          │    │
│  │                      (云端 MySQL 8.0+)                            │    │
│  │                                                                  │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │    │
│  │   │ memories    │  │ agents      │  │ acl         │           │    │
│  │   │ 记忆表      │  │ Agent注册表  │  │ 访问控制表  │           │    │
│  │   └─────────────┘  └─────────────┘  └─────────────┘           │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Storage Layer (存储适配层)                    │    │
│  │                                                                  │    │
│  │   ┌─────────────────────────────────────────────────────────┐  │    │
│  │   │              MySQLConnectionPool                         │  │    │
│  │   │              (连接池管理)                                │  │    │
│  │   └─────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Core Engine                                  │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │
│  │   │ StoreEngine │  │SearchEngine│  │  ACLEngine  │          │    │
│  │   └─────────────┘  └─────────────┘  └─────────────┘          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Interface Layer                              │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │
│  │   │    CLI     │  │   REST API  │  │    SDK     │          │    │
│  │   └─────────────┘  └─────────────┘  └─────────────┘          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    ↑                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Plugin Adapters                                │    │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │    │
│  │   │OpenClaw│  │Claude   │  │ Codex   │  │Kimi Code│  Cursor │  │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘─────────┘    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. MySQL Schema 设计

```sql
-- ============================================
-- Agent Memory System - MySQL Schema
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS agent_memory
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agent_memory;

-- 共享记忆表
CREATE TABLE IF NOT EXISTS memories (
    id VARCHAR(50) PRIMARY KEY COMMENT '记忆ID，格式: mem_xxxxxxxxxx',
    content TEXT NOT NULL COMMENT '记忆内容',
    summary VARCHAR(500) COMMENT '摘要',
    type ENUM('general', 'project', 'preference', 'knowledge', 'team') 
        NOT NULL DEFAULT 'general' COMMENT '记忆类型',
    visibility ENUM('private', 'shared', 'global') 
        NOT NULL DEFAULT 'shared' COMMENT '可见性',
    source ENUM('cli', 'openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor') 
        NOT NULL DEFAULT 'cli' COMMENT '来源',
    source_agent VARCHAR(100) COMMENT '来源Agent ID',
    project_path VARCHAR(500) COMMENT '关联项目路径',
    importance DECIMAL(3,1) DEFAULT 5.0 COMMENT '重要性 1-10',
    tags JSON COMMENT '标签列表',
    created_at BIGINT NOT NULL COMMENT '创建时间戳(ms)',
    updated_at BIGINT NOT NULL COMMENT '更新时间戳(ms)',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
    
    INDEX idx_type (type),
    INDEX idx_visibility (visibility),
    INDEX idx_project (project_path(255)),
    INDEX idx_source (source),
    INDEX idx_created (created_at DESC),
    INDEX idx_deleted (is_deleted),
    FULLTEXT INDEX ft_content (content, summary)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agent 注册表
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(100) PRIMARY KEY COMMENT 'Agent ID',
    type ENUM('openclaw', 'claude_code', 'codex', 'kimi_code', 'cursor', 'other') 
        NOT NULL COMMENT 'Agent类型',
    name VARCHAR(100) COMMENT '显示名称',
    api_key_hash VARCHAR(255) COMMENT 'API Key hash',
    registered_at BIGINT NOT NULL COMMENT '注册时间',
    last_seen BIGINT COMMENT '最后活跃时间',
    
    INDEX idx_type (type),
    INDEX idx_last_seen (last_seen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 访问控制表
CREATE TABLE IF NOT EXISTS acl (
    memory_id VARCHAR(50) NOT NULL COMMENT '记忆ID',
    agent_id VARCHAR(100) NOT NULL COMMENT 'Agent ID',
    permission ENUM('read', 'write', 'admin') NOT NULL DEFAULT 'read' COMMENT '权限',
    granted_by VARCHAR(100) NOT NULL COMMENT '授权者',
    granted_at BIGINT NOT NULL COMMENT '授权时间',
    expires_at BIGINT COMMENT '过期时间',
    
    PRIMARY KEY (memory_id, agent_id),
    INDEX idx_agent (agent_id),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 向量缓存表 (可选，用于 embeddings)
CREATE TABLE IF NOT EXISTS embeddings (
    content_hash VARCHAR(64) PRIMARY KEY COMMENT '内容SHA256',
    embedding BLOB COMMENT '向量数据',
    model VARCHAR(50) COMMENT '嵌入模型',
    dimension INT COMMENT '向量维度',
    created_at BIGINT COMMENT '创建时间',
    
    INDEX idx_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 搜索历史表
CREATE TABLE IF NOT EXISTS search_history (
    id VARCHAR(50) PRIMARY KEY COMMENT '搜索ID',
    query TEXT NOT NULL COMMENT '搜索内容',
    agent_id VARCHAR(100) NOT NULL COMMENT '搜索者',
    results_count INT DEFAULT 0 COMMENT '结果数量',
    latency_ms INT COMMENT '延迟',
    searched_at BIGINT NOT NULL COMMENT '搜索时间',
    
    INDEX idx_agent (agent_id),
    INDEX idx_searched (searched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 3. 数据库配置

```yaml
# config.yaml

database:
  # MySQL 连接配置
  host: "your-mysql-host.cloud.com"
  port: 3306
  database: "agent_memory"
  username: "memory_user"
  password: "${MYSQL_PASSWORD}"  # 从环境变量读取
  charset: "utf8mb4"
  
  # 连接池配置
  pool:
    min_size: 5
    max_size: 20
    max_idle_time: 300  # 秒
    pool_recycle: 3600  # 秒
  
  # MySQL 特定优化
  options:
    connect_timeout: 10
    read_timeout: 30
    write_timeout: 30

# 向量搜索 (可选)
vector:
  enabled: false  # MySQL 8.0+ 原生向量支持
  # 或使用外部向量数据库
  provider: "milvus"  # milvus / qdrant / pinecone
  host: "your-vector-db.cloud.com"
  port: 19530
```

---

## 4. 核心模块修改

### 4.1 数据库层

```
SQLite → MySQL

主要修改:
1. sqlite3 → PyMySQL
2. 连接池管理 (DBUtils.PooledDB)
3. SQL 语法调整
4. 事务处理
5. 错误重试
```

### 4.2 搜索增强

```
本地 SQLite (Phase 1)    →    MySQL + 全文索引

关键词搜索: LIKE → FULLTEXT INDEX
向量搜索:   无 → MySQL 8.0 原生向量 或 Milvus/Pinecone
```

---

## 5. 技术栈

| 组件 | 选择 | 原因 |
|------|------|------|
| **数据库** | MySQL 8.0+ | 用户提供 |
| **连接池** | DBUtils + PyMySQL | 高性能连接池 |
| **ORM** | SQLAlchemy (可选) | 简化查询 |
| **向量** | MySQL 原生向量 或 Milvus | 取决于数据量 |
| **API** | FastAPI | 高性能异步 |
| **CLI** | Python 原生 | 零依赖 |

---

## 6. 与 SQLite 版本的对比

| 特性 | SQLite 本地版 | MySQL 云端版 |
|------|---------------|--------------|
| **部署** | 无需部署 | 需要 MySQL 云端 |
| **共享** | 文件共享麻烦 | 原生支持 |
| **并发** | WAL 模式一般 | 高并发 |
| **数据量** | 小 (< 100万) | 大规模 |
| **向量搜索** | 需外挂 | MySQL 8.0 内置 / Milvus |
| **延迟** | 低 (本地) | 受网络影响 |
| **成本** | 低 | 云端 MySQL 费用 |

---

## 7. 安全考虑

```yaml
# 安全配置

security:
  # API 认证
  api_key:
    enabled: true
    header: "X-API-Key"
    
  # Agent 认证
  agent_auth:
    enabled: true
    method: "api_key"  # api_key / jwt / oauth2
    
  # 传输加密
  tls:
    enabled: true  # 生产环境必须开启
    verify: true
    
  # SQL 注入防护
  # 使用参数化查询，ORM 自动处理
```

---

## 8. 连接配置示例

```python
# 数据库连接配置

import os
from dbutils.pooled_db import PooledDB
import pymysql

# MySQL 连接池
pool = PooledDB(
    creator=pymysql,
    maxconnections=20,
    mincached=5,
    maxcached=10,
    blocking=True,
    
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    database=os.getenv("MYSQL_DATABASE", "agent_memory"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    charset="utf8mb4",
    
    connect_timeout=10,
    read_timeout=30,
    write_timeout=30,
)

# 使用
with pool.connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM memories LIMIT 10")
        results = cursor.fetchall()
```
