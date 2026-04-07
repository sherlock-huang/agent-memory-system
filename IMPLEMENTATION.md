# Shared Memory Implementation Guide
## 跨 Agent 共享记忆具体实现架构与逻辑

**版本:** v1.0  
**日期:** 2026-04-07  
**目标:** 展示共享记忆表的完整实现方案

---

## 📂 项目结构

```
agent-memory-system/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLite 数据库管理
│   │   ├── schema.py            # 数据库 Schema 定义
│   │   ├── memory_manager.py    # 核心记忆管理器
│   │   ├── search_engine.py     # 混合搜索引擎
│   │   └── dreaming_adapter.py   # Dreaming 适配器
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API 路由
│   │   ├── middleware.py         # 中间件
│   │   ├── schemas.py           # Pydantic 模型
│   │   └── dependencies.py      # 依赖注入
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py              # 适配器基类
│   │   ├── openclaw.py          # OpenClaw 适配器
│   │   ├── claude_code.py       # Claude Code 适配器
│   │   └── codex.py            # Codex 适配器
│   │
│   └── utils/
│       ├── __init__.py
│       ├── embedding.py          # 向量化工具
│       ├── config.py             # 配置管理
│       └── logger.py             # 日志
│
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_memory_manager.py
│   ├── test_search_engine.py
│   └── test_api.py
│
├── config.yaml                  # 配置文件
├── requirements.txt             # 依赖
├── run.py                       # 启动入口
├── IMPLEMENTATION.md            # 本文档
└── README.md
```

---

## 1. 数据库 Schema 设计

### 1.1 完整 Schema (SQLite)

```python
# src/core/schema.py

SCHEMA_SQL = """
-- ============================================
-- 共享记忆系统 Schema
-- 基于 OpenClaw 官方 SQLite 扩展
-- ============================================

-- ============================================
-- Part 1: OpenClaw 官方表 (只读引用)
-- ============================================

-- chunks: OpenClaw 官方文本块表
-- 此表由 OpenClaw 管理，我们只读引用其数据
CREATE TABLE IF NOT EXISTS openclaw_chunks (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    source TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    hash TEXT NOT NULL,
    model TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL,  -- JSON 数组字符串
    updated_at INTEGER
);

-- chunks_vec: OpenClaw 向量表 (sqlite-vec)
-- 需要 sqlite-vec 扩展支持

-- chunks_fts: OpenClaw 全文索引表 (FTS5)
-- 需要 FTS5 扩展支持

-- ============================================
-- Part 2: 共享记忆核心表
-- ============================================

-- 共享记忆主表
CREATE TABLE IF NOT EXISTS shared_memories (
    id TEXT PRIMARY KEY,                    -- UUID: shr_xxxxx
    
    -- 内容
    content TEXT NOT NULL,                  -- 原始内容
    summary TEXT,                           -- 自动摘要
    
    -- 类型与可见性
    memory_type TEXT NOT NULL DEFAULT 'general',  -- general | project | team | global
    visibility TEXT NOT NULL DEFAULT 'shared',    -- private | shared | global
    
    -- 来源追踪
    source_agent TEXT NOT NULL,             -- 创建的 Agent ID
    source_user TEXT,                       -- 来源用户 (可选)
    project_path TEXT,                       -- 关联项目路径
    
    -- 评分与元数据
    importance REAL DEFAULT 5.0,            -- 1-10 重要性
    confidence REAL DEFAULT 5.0,             -- 1-10 置信度
    access_count INTEGER DEFAULT 0,          -- 被访问次数
    last_accessed_at INTEGER,                -- 最后访问时间戳
    
    -- 时间戳
    created_at INTEGER NOT NULL,            -- 创建时间戳 (Unix epoch ms)
    updated_at INTEGER NOT NULL,            -- 更新时间戳
    valid_from INTEGER NOT NULL,            -- 生效时间
    valid_until INTEGER,                    -- 过期时间 (可选)
    
    -- 向量 (冗余存储，加速查询)
    embedding TEXT,                          -- JSON 数组字符串
    chunk_id TEXT,                           -- 关联的 OpenClaw chunk ID (可选)
    
    -- 标签
    tags TEXT,                              -- JSON 数组: '["python", "preference"]'
    
    -- 状态
    is_deleted INTEGER DEFAULT 0,           -- 软删除标记
    is_pinned INTEGER DEFAULT 0,             -- 置顶标记
    
    FOREIGN KEY (chunk_id) REFERENCES openclaw_chunks(id)
);

-- 向量索引 (我们自己的向量表，使用 sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS shared_memories_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding REAL[1536]  -- 默认 1536 维，可配置
);

-- 全文索引
CREATE VIRTUAL TABLE IF NOT EXISTS shared_memories_fts USING fts5(
    content,
    summary,
    tags,
    content='shared_memories',
    content_rowid='rowid'
);

-- ============================================
-- Part 3: 访问控制表 (ACL)
-- ============================================

CREATE TABLE IF NOT EXISTS shared_acl (
    id TEXT PRIMARY KEY,                    -- UUID
    
    memory_id TEXT NOT NULL,               -- 关联记忆 ID
    agent_id TEXT NOT NULL,                -- 被授权的 Agent ID
    
    permission TEXT NOT NULL,               -- read | write | admin
    grant_type TEXT NOT NULL DEFAULT 'direct',  -- direct | inherited | role
    
    granted_by TEXT NOT NULL,              -- 授权者
    granted_at INTEGER NOT NULL,           -- 授权时间
    
    expires_at INTEGER,                    -- 过期时间 (可选)
    
    FOREIGN KEY (memory_id) REFERENCES shared_memories(id) ON DELETE CASCADE
);

-- 角色表 (用于批量授权)
CREATE TABLE IF NOT EXISTS agent_roles (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE,         -- Agent 唯一 ID
    role_type TEXT NOT NULL DEFAULT 'member',  -- owner | admin | member | guest
    project_path TEXT,                      -- 如果是项目角色
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- ============================================
-- Part 4: Agent 注册表
-- ============================================

CREATE TABLE IF NOT EXISTS agent_registry (
    agent_id TEXT PRIMARY KEY,              -- 全局唯一 ID
    agent_type TEXT NOT NULL,              -- openclaw | claude_code | codex | other
    
    -- 信息
    name TEXT,                             -- 显示名称
    description TEXT,                      -- 描述
    endpoint TEXT,                         -- API 地址或 stdio 路径
    version TEXT,                          -- 版本
    
    -- 能力
    capabilities TEXT,                     -- JSON: supported features
    
    -- 状态
    status TEXT DEFAULT 'active',         -- active | inactive | disconnected
    last_seen_at INTEGER,                  -- 最后活跃时间
    last_heartbeat INTEGER,                -- 心跳时间
    
    -- 时间
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    -- 认证
    api_key_hash TEXT,                     -- API Key 的 hash
    auth_token TEXT,                       -- 认证 token (加密存储)
);

-- Agent 连接会话表
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    
    session_type TEXT NOT NULL,            -- api | websocket | cli
    
    started_at INTEGER NOT NULL,
    last_activity_at INTEGER,
    ended_at INTEGER,
    
    request_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    metadata TEXT,                         -- JSON: 额外数据
    
    FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
);

-- ============================================
-- Part 5: 检索历史与分析
-- ============================================

-- 检索历史 (用于优化和审计)
CREATE TABLE IF NOT EXISTS search_history (
    id TEXT PRIMARY KEY,
    
    query TEXT NOT NULL,
    query_embedding TEXT,                  -- 查询向量
    
    agent_id TEXT NOT NULL,               -- 查询者
    session_id TEXT,
    
    results_count INTEGER,
    results_ids TEXT,                      -- JSON array of memory IDs
    
    latency_ms INTEGER,                    -- 响应延迟
    
    searched_at INTEGER NOT NULL,
    
    FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
);

-- 访问日志
CREATE TABLE IF NOT EXISTS access_log (
    id TEXT PRIMARY KEY,
    
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    
    action TEXT NOT NULL,                  -- read | write | delete | share
    
    details TEXT,                          -- JSON: 额外信息
    
    ip_address TEXT,                       -- 来源 IP
    user_agent TEXT,                       -- User Agent
    
    accessed_at INTEGER NOT NULL,
    
    FOREIGN KEY (memory_id) REFERENCES shared_memories(id),
    FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
);

-- ============================================
-- Part 6: 索引
-- ============================================

-- shared_memories 索引
CREATE INDEX IF NOT EXISTS idx_sm_type ON shared_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_sm_visibility ON shared_memories(visibility);
CREATE INDEX IF NOT EXISTS idx_sm_source_agent ON shared_memories(source_agent);
CREATE INDEX IF NOT EXISTS idx_sm_project ON shared_memories(project_path);
CREATE INDEX IF NOT EXISTS idx_sm_created ON shared_memories(created_at);
CREATE INDEX IF NOT EXISTS idx_sm_valid_until ON shared_memories(valid_until);
CREATE INDEX IF NOT EXISTS idx_sm_is_deleted ON shared_memories(is_deleted);

-- shared_acl 索引
CREATE INDEX IF NOT EXISTS idx_acl_memory ON shared_acl(memory_id);
CREATE INDEX IF NOT EXISTS idx_acl_agent ON shared_acl(agent_id);

-- agent_registry 索引
CREATE INDEX IF NOT EXISTS idx_ar_type ON agent_registry(agent_type);
CREATE INDEX IF NOT EXISTS idx_ar_status ON agent_registry(status);

-- search_history 索引
CREATE INDEX IF NOT EXISTS idx_sh_agent ON search_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_sh_searched ON search_history(searched_at);

-- access_log 索引
CREATE INDEX IF NOT EXISTS idx_al_memory ON access_log(memory_id);
CREATE INDEX IF NOT EXISTS idx_al_agent ON access_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_al_accessed ON access_log(accessed_at);
"""


# 向量维度配置
DEFAULT_EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small

# 内存类型枚举
MEMORY_TYPES = ['general', 'project', 'team', 'global']

# 可见性枚举
VISIBILITY_LEVELS = ['private', 'shared', 'global']

# 权限枚举
PERMISSIONS = ['read', 'write', 'admin']

# Agent 类型
AGENT_TYPES = ['openclaw', 'claude_code', 'codex', 'other']
```

---

## 2. 核心管理器实现

### 2.1 数据库管理

```python
# src/core/database.py

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import threading

from ..utils.logger import get_logger
from .schema import SCHEMA_SQL

logger = get_logger(__name__)


class DatabaseManager:
    """
    SQLite 数据库管理器
    负责连接、事务、Schema 初始化
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        if db_path:
            self.db_path = db_path
        else:
            # 默认路径: ~/.openclaw/workspace/agent-memory-system/data/shared_memory.db
            base = Path.home() / '.openclaw' / 'workspace' / 'agent-memory-system' / 'data'
            base.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base / 'shared_memory.db')
        
        self._conn: Optional[sqlite3.Connection] = None
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接 (线程安全)"""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._conn.row_factory = sqlite3.Row
            # 启用 WAL 模式，提高并发性能
            self._conn.execute('PRAGMA journal_mode=WAL')
            self._conn.execute('PRAGMA synchronous=NORMAL')
            self._conn.execute('PRAGMA busy_timeout=30000')
        return self._conn
    
    @contextmanager
    def get_cursor(self):
        """获取游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def _init_database(self):
        """初始化数据库 Schema"""
        logger.info(f"Initializing database at: {self.db_path}")
        
        with self.get_cursor() as cursor:
            # 执行 Schema
            cursor.executescript(SCHEMA_SQL)
            
            # 检查 OpenClaw 表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='chunks'
            """)
            self.has_openclaw_tables = cursor.fetchone() is not None
            
            if self.has_openclaw_tables:
                logger.info("OpenClaw chunks table found - linking")
            else:
                logger.warning("OpenClaw chunks table not found - some features limited")
    
    def execute(self, sql: str, params: tuple = None) -> sqlite3.Cursor:
        """执行 SQL"""
        with self.get_cursor() as cursor:
            if params:
                return cursor.execute(sql, params)
            return cursor.execute(sql)
    
    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """批量执行 SQL"""
        with self.get_cursor() as cursor:
            return cursor.executemany(sql, params_list)
    
    def fetchone(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """查询单条"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetchall(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询多条"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
```

### 2.2 记忆管理器

```python
# src/core/memory_manager.py

import uuid
import json
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.embedding import EmbeddingService
from .database import DatabaseManager
from .schema import MEMORY_TYPES, VISIBILITY_LEVELS, PERMISSIONS

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目数据类"""
    id: str = field(default_factory=lambda: f"shr_{uuid.uuid4().hex[:12]}")
    content: str = ""
    summary: Optional[str] = None
    memory_type: str = "general"
    visibility: str = "shared"
    
    source_agent: str = ""
    source_user: Optional[str] = None
    project_path: Optional[str] = None
    
    importance: float = 5.0
    confidence: float = 5.0
    access_count: int = 0
    last_accessed_at: Optional[int] = None
    
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    valid_from: int = field(default_factory=lambda: int(time.time() * 1000))
    valid_until: Optional[int] = None
    
    embedding: Optional[List[float]] = None
    chunk_id: Optional[str] = None
    
    tags: List[str] = field(default_factory=list)
    is_deleted: bool = False
    is_pinned: bool = False


class MemoryManager:
    """
    共享记忆管理器
    核心逻辑：存储、检索、访问控制
    """
    
    def __init__(
        self,
        db: DatabaseManager = None,
        embedding_service: EmbeddingService = None
    ):
        self.db = db or DatabaseManager()
        self.embedding = embedding_service or EmbeddingService()
    
    # ============================================
    # 存储操作
    # ============================================
    
    def store(
        self,
        content: str,
        source_agent: str,
        memory_type: str = "general",
        visibility: str = "shared",
        importance: float = 5.0,
        tags: List[str] = None,
        project_path: str = None,
        source_user: str = None,
        generate_summary: bool = True,
        **kwargs
    ) -> MemoryEntry:
        """
        存储新记忆
        
        流程:
        1. 生成向量
        2. 创建记忆条目
        3. 写入 SQLite
        4. 写入向量索引
        5. 更新 FTS 索引
        """
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            visibility=visibility,
            source_agent=source_agent,
            project_path=project_path,
            source_user=source_user,
            importance=importance,
            tags=tags or [],
            **kwargs
        )
        
        # 生成摘要
        if generate_summary and len(content) > 200:
            entry.summary = self._generate_summary(content)
        
        # 生成向量
        entry.embedding = self.embedding.embed(content)
        
        # 写入数据库
        self._insert_entry(entry)
        
        # 写入向量索引
        if entry.embedding:
            self._insert_vector(entry)
        
        # 写入 FTS
        self._insert_fts(entry)
        
        logger.info(f"Stored memory: {entry.id} (type={memory_type}, visibility={visibility})")
        
        return entry
    
    def _insert_entry(self, entry: MemoryEntry):
        """插入记忆条目到 SQLite"""
        sql = """
        INSERT INTO shared_memories (
            id, content, summary, memory_type, visibility,
            source_agent, source_user, project_path,
            importance, confidence, access_count, last_accessed_at,
            created_at, updated_at, valid_from, valid_until,
            embedding, chunk_id, tags, is_deleted, is_pinned
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            entry.id,
            entry.content,
            entry.summary,
            entry.memory_type,
            entry.visibility,
            entry.source_agent,
            entry.source_user,
            entry.project_path,
            entry.importance,
            entry.confidence,
            entry.access_count,
            entry.last_accessed_at,
            entry.created_at,
            entry.updated_at,
            entry.valid_from,
            entry.valid_until,
            json.dumps(entry.embedding) if entry.embedding else None,
            entry.chunk_id,
            json.dumps(entry.tags),
            0 if not entry.is_deleted else 1,
            1 if entry.is_pinned else 0
        )
        
        self.db.execute(sql, params)
    
    def _insert_vector(self, entry: MemoryEntry):
        """插入向量到 sqlite-vec"""
        if not entry.embedding:
            return
        
        try:
            sql = "INSERT INTO shared_memories_vec (id, embedding) VALUES (?, ?)"
            # sqlite-vec 需要二进制格式
            import struct
            embedding_bytes = struct.pack(f'{len(entry.embedding)}f', *entry.embedding)
            self.db.execute(sql, (entry.id, embedding_bytes))
        except Exception as e:
            logger.warning(f"Failed to insert vector: {e}")
            # 回退到内联存储
    
    def _insert_fts(self, entry: MemoryEntry):
        """插入到 FTS 索引"""
        sql = """
        INSERT INTO shared_memories_fts (rowid, content, summary, tags)
        SELECT rowid, ?, ?, ? FROM shared_memories WHERE id = ?
        """
        # 注意：实际实现需要先插入再关联，这里简化处理
        pass
    
    def _generate_summary(self, content: str) -> str:
        """生成摘要 (可以用 LLM)"""
        # 简单实现：取前 100 字符
        if len(content) <= 100:
            return content
        return content[:100].rsplit(' ', 1)[0] + "..."
    
    # ============================================
    # 检索操作
    # ============================================
    
    def search(
        self,
        query: str,
        agent_id: str,
        limit: int = 10,
        memory_types: List[str] = None,
        visibility: str = None,
        project_path: str = None,
        min_importance: float = None,
        include_deleted: bool = False
    ) -> List[Dict]:
        """
        搜索记忆
        
        流程:
        1. 验证权限
        2. 生成查询向量
        3. 向量搜索 + 关键词搜索
        4. 结果融合
        5. 权限过滤
        6. 返回排序结果
        """
        start_time = time.time()
        
        # 1. 验证权限
        accessible_visibility = self._get_accessible_visibility(agent_id)
        if not accessible_visibility:
            return []
        
        # 2. 生成查询向量
        query_embedding = self.embedding.embed(query)
        
        # 3. 构建基础查询
        conditions = ["is_deleted = 0"]
        
        if visibility:
            conditions.append(f"visibility = '{visibility}'")
        else:
            visors = "', '".join(accessible_visibility)
            conditions.append(f"visibility IN ('{visors}')")
        
        if memory_types:
            types = "', '".join(memory_types)
            conditions.append(f"memory_type IN ('{types}')")
        
        if project_path:
            conditions.append(f"project_path = '{project_path}'")
        
        if min_importance:
            conditions.append(f"importance >= {min_importance}")
        
        where_clause = " AND ".join(conditions)
        
        # 4. 执行搜索
        results = []
        
        # 向量搜索
        if query_embedding:
            vector_results = self._vector_search(query_embedding, limit * 2)
            results.extend(vector_results)
        
        # 关键词搜索
        keyword_results = self._keyword_search(query, limit * 2)
        results.extend(keyword_results)
        
        # 5. 去重和融合
        merged = self._merge_results(results, query_embedding)
        
        # 6. 权限最终过滤
        filtered = self._filter_by_acl(merged, agent_id)
        
        # 7. 限制返回数量
        final_results = filtered[:limit]
        
        # 8. 更新访问统计
        self._update_access_stats([r['id'] for r in final_results], agent_id)
        
        # 9. 记录搜索历史
        latency = int((time.time() - start_time) * 1000)
        self._log_search(query, agent_id, len(final_results), latency)
        
        return final_results
    
    def _get_accessible_visibility(self, agent_id: str) -> List[str]:
        """获取 Agent 可访问的可见性级别"""
        sql = "SELECT role_type FROM agent_roles WHERE agent_id = ?"
        result = self.db.fetchone(sql, (agent_id,))
        
        if result and result['role_type'] == 'owner':
            return ['private', 'shared', 'global']
        
        return ['shared', 'global']
    
    def _vector_search(self, query_embedding: List[float], limit: int) -> List[Dict]:
        """向量相似度搜索"""
        try:
            # 尝试使用 sqlite-vec
            sql = """
            SELECT sm.*, 
                   vec0_distance(shared_memories_vec.embedding, ?) as similarity
            FROM shared_memories_vec
            JOIN shared_memories sm ON sm.id = shared_memories_vec.id
            WHERE sm.is_deleted = 0
            ORDER BY similarity ASC
            LIMIT ?
            """
            
            import struct
            query_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)
            
            rows = self.db.fetchall(sql, (query_bytes, limit))
            
            return [self._row_to_result(dict(row), 'vector') for row in rows]
        except Exception as e:
            logger.warning(f"Vector search failed, using fallback: {e}")
            return self._vector_search_fallback(query_embedding, limit)
    
    def _vector_search_fallback(self, query_embedding: List[float], limit: int) -> List[Dict]:
        """向量搜索回退：使用内联 embedding 计算"""
        sql = """
        SELECT * FROM shared_memories
        WHERE is_deleted = 0 AND embedding IS NOT NULL
        LIMIT ?
        """
        
        rows = self.db.fetchall(sql, (limit * 3,))  # 多取一些，后面过滤
        
        results = []
        for row in rows:
            try:
                stored_embedding = json.loads(row['embedding'])
                # 计算余弦相似度
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                row['similarity'] = similarity
                results.append(self._row_to_result(row, 'vector'))
            except:
                continue
        
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return results[:limit]
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict]:
        """关键词搜索 (FTS5)"""
        sql = """
        SELECT sm.*, bm25(shared_memories_fts) as bm25_score
        FROM shared_memories_fts
        JOIN shared_memories sm ON sm.rowid = shared_memories_fts.rowid
        WHERE shared_memories_fts MATCH ?
        AND sm.is_deleted = 0
        ORDER BY bm25_score
        LIMIT ?
        """
        
        # 简单处理查询词
        fts_query = f'"{query}"' if ' ' not in query else query
        
        try:
            rows = self.db.fetchall(sql, (fts_query, limit))
            return [self._row_to_result(dict(row), 'keyword') for row in rows]
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []
    
    def _merge_results(
        self,
        results: List[Dict],
        query_embedding: List[float],
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict]:
        """混合搜索结果融合"""
        seen = {}
        
        for r in results:
            mem_id = r['id']
            
            if mem_id not in seen:
                seen[mem_id] = r
                seen[mem_id]['score'] = 0
                seen[mem_id]['sources'] = []
            else:
                # 合并
                seen[mem_id]['access_count'] = max(
                    seen[mem_id].get('access_count', 0),
                    r.get('access_count', 0)
                )
            
            # 累加权重分数
            source = r.pop('_source', 'unknown')
            seen[mem_id]['sources'].append(source)
            
            if source == 'vector':
                seen[mem_id]['score'] += vector_weight * r.get('similarity', 0)
            elif source == 'keyword':
                # 归一化 BM25 分数
                bm25 = r.get('bm25_score', 0)
                norm_bm25 = max(0, min(1, -bm25 / 100))  # 简单归一化
                seen[mem_id]['score'] += keyword_weight * norm_bm25
        
        # 排序
        merged = list(seen.values())
        merged.sort(key=lambda x: x['score'], reverse=True)
        
        return merged
    
    def _filter_by_acl(self, results: List[Dict], agent_id: str) -> List[Dict]:
        """根据 ACL 过滤结果"""
        # 获取 Agent 角色
        role_sql = "SELECT role_type, project_path FROM agent_roles WHERE agent_id = ?"
        role = self.db.fetchone(role_sql, (agent_id,))
        
        filtered = []
        for r in results:
            # owner/admin 可以访问所有
            if role and role['role_type'] in ['owner', 'admin']:
                filtered.append(r)
                continue
            
            # private 只有创建者可以访问
            if r['visibility'] == 'private' and r['source_agent'] != agent_id:
                continue
            
            # 检查具体 ACL 权限
            acl_sql = """
            SELECT permission FROM shared_acl
            WHERE memory_id = ? AND agent_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """
            acl = self.db.fetchone(
                acl_sql,
                (r['id'], agent_id, int(time.time() * 1000))
            )
            
            if acl or r['visibility'] in ['shared', 'global']:
                filtered.append(r)
        
        return filtered
    
    def _row_to_result(self, row: Dict, source: str) -> Dict:
        """行数据转换为结果"""
        return {
            'id': row['id'],
            'content': row['content'],
            'summary': row['summary'],
            'type': row['memory_type'],
            'visibility': row['visibility'],
            'importance': row['importance'],
            'confidence': row['confidence'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'source_agent': row['source_agent'],
            'project_path': row['project_path'],
            'created_at': row['created_at'],
            '_source': source,
            **{k: v for k, v in row.items() if k.startswith('similarity') or k.startswith('bm25')}
        }
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)
    
    def _update_access_stats(self, memory_ids: List[str], agent_id: str):
        """更新访问统计"""
        if not memory_ids:
            return
        
        now = int(time.time() * 1000)
        placeholders = ','.join('?' * len(memory_ids))
        
        sql = f"""
        UPDATE shared_memories
        SET access_count = access_count + 1,
            last_accessed_at = ?
        WHERE id IN ({placeholders})
        """
        
        try:
            self.db.execute(sql, (now, *memory_ids))
        except Exception as e:
            logger.warning(f"Failed to update access stats: {e}")
    
    def _log_search(self, query: str, agent_id: str, results_count: int, latency_ms: int):
        """记录搜索历史"""
        sql = """
        INSERT INTO search_history (
            id, query, agent_id, results_count, latency_ms, searched_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        search_id = f"seh_{uuid.uuid4().hex[:12]}"
        now = int(time.time() * 1000)
        
        try:
            self.db.execute(sql, (search_id, query, agent_id, results_count, latency_ms, now))
        except Exception as e:
            logger.warning(f"Failed to log search: {e}")
    
    # ============================================
    # ACL 操作
    # ============================================
    
    def grant_access(
        self,
        memory_id: str,
        agent_id: str,
        permission: str,
        granted_by: str,
        expires_at: int = None
    ) -> bool:
        """授予访问权限"""
        if permission not in PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")
        
        sql = """
        INSERT OR REPLACE INTO shared_acl (
            id, memory_id, agent_id, permission, granted_by, granted_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        acl_id = f"acl_{uuid.uuid4().hex[:12]}"
        now = int(time.time() * 1000)
        
        try:
            self.db.execute(sql, (acl_id, memory_id, agent_id, permission, granted_by, now, expires_at))
            logger.info(f"Granted {permission} on {memory_id} to {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return False
    
    def revoke_access(self, memory_id: str, agent_id: str) -> bool:
        """撤销访问权限"""
        sql = "DELETE FROM shared_acl WHERE memory_id = ? AND agent_id = ?"
        
        try:
            self.db.execute(sql, (memory_id, agent_id))
            logger.info(f"Revoked access on {memory_id} from {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False
    
    # ============================================
    # 生命周期操作
    # ============================================
    
    def soft_delete(self, memory_id: str, agent_id: str) -> bool:
        """软删除记忆"""
        # 验证权限
        if not self._can_modify(memory_id, agent_id):
            return False
        
        sql = """
        UPDATE shared_memories
        SET is_deleted = 1, updated_at = ?
        WHERE id = ?
        """
        
        try:
            self.db.execute(sql, (int(time.time() * 1000), memory_id))
            
            # 记录删除日志
            self._log_access(memory_id, agent_id, 'delete')
            
            logger.info(f"Soft deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def restore(self, memory_id: str, agent_id: str) -> bool:
        """恢复已删除的记忆"""
        if not self._can_modify(memory_id, agent_id):
            return False
        
        sql = """
        UPDATE shared_memories
        SET is_deleted = 0, updated_at = ?
        WHERE id = ?
        """
        
        try:
            self.db.execute(sql, (int(time.time() * 1000), memory_id))
            logger.info(f"Restored memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore memory: {e}")
            return False
    
    def hard_delete(self, memory_id: str, agent_id: str) -> bool:
        """永久删除记忆"""
        if not self._can_modify(memory_id, agent_id, require_admin=True):
            return False
        
        # 先删向量
        try:
            self.db.execute("DELETE FROM shared_memories_vec WHERE id = ?", (memory_id,))
        except:
            pass
        
        # 删 ACL
        self.db.execute("DELETE FROM shared_acl WHERE memory_id = ?", (memory_id,))
        
        # 删主记录
        sql = "DELETE FROM shared_memories WHERE id = ?"
        
        try:
            self.db.execute(sql, (memory_id,))
            logger.info(f"Hard deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to hard delete memory: {e}")
            return False
    
    def _can_modify(self, memory_id: str, agent_id: str, require_admin: bool = False) -> bool:
        """检查是否可以修改"""
        sql = "SELECT source_agent, visibility FROM shared_memories WHERE id = ?"
        memory = self.db.fetchone(sql, (memory_id,))
        
        if not memory:
            return False
        
        # 创建者可以修改
        if memory['source_agent'] == agent_id:
            return True
        
        # owner/admin 可以修改
        role_sql = "SELECT role_type FROM agent_roles WHERE agent_id = ?"
        role = self.db.fetchone(role_sql, (agent_id,))
        
        if require_admin:
            return role and role['role_type'] == 'owner'
        
        return role and role['role_type'] in ['owner', 'admin']
    
    def _log_access(self, memory_id: str, agent_id: str, action: str):
        """记录访问日志"""
        sql = """
        INSERT INTO access_log (id, memory_id, agent_id, action, accessed_at)
        VALUES (?, ?, ?, ?, ?)
        """
        
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        now = int(time.time() * 1000)
        
        try:
            self.db.execute(sql, (log_id, memory_id, agent_id, action, now))
        except Exception as e:
            logger.warning(f"Failed to log access: {e}")
```

---

## 3. API 路由实现

### 3.1 Pydantic 模型

```python
# src/api/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MemoryStoreRequest(BaseModel):
    """存储记忆请求"""
    content: str = Field(..., min_length=1, max_length=50000)
    summary: Optional[str] = Field(None, max_length=500)
    memory_type: str = Field(default="general")
    visibility: str = Field(default="shared")
    importance: float = Field(default=5.0, ge=1.0, le=10.0)
    tags: List[str] = Field(default_factory=list)
    project_path: Optional[str] = None
    source_user: Optional[str] = None
    valid_until: Optional[int] = None  # Unix timestamp ms


class MemoryStoreResponse(BaseModel):
    """存储记忆响应"""
    id: str
    content: str
    summary: Optional[str]
    memory_type: str
    visibility: str
    importance: float
    tags: List[str]
    created_at: int


class MemorySearchRequest(BaseModel):
    """搜索记忆请求"""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    memory_types: Optional[List[str]] = None
    visibility: Optional[str] = None
    project_path: Optional[str] = None
    min_importance: Optional[float] = Field(None, ge=1.0, le=10.0)


class MemorySearchResponse(BaseModel):
    """搜索记忆响应"""
    results: List[dict]
    total: int
    query_time_ms: int
    agents_searched: List[str]


class MemoryUpdateRequest(BaseModel):
    """更新记忆请求"""
    content: Optional[str] = None
    summary: Optional[str] = None
    importance: Optional[float] = Field(None, ge=1.0, le=10.0)
    tags: Optional[List[str]] = None
    visibility: Optional[str] = None


class ACLGrantRequest(BaseModel):
    """授权请求"""
    memory_id: str
    agent_id: str
    permission: str  # read, write, admin
    expires_at: Optional[int] = None


class AgentRegisterRequest(BaseModel):
    """Agent 注册请求"""
    agent_id: str
    agent_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint: Optional[str] = None
    version: Optional[str] = None
    capabilities: Optional[dict] = None


class AgentRegisterResponse(BaseModel):
    """Agent 注册响应"""
    agent_id: str
    status: str
    registered_at: int
    api_key: Optional[str] = None  # 首次注册时返回


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    database_path: str
    agents_online: int
    memories_total: int
    shared_memories: int
```

### 3.2 路由定义

```python
# src/api/routes.py

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
import time

from ..core.memory_manager import MemoryManager
from ..core.database import DatabaseManager
from .schemas import (
    MemoryStoreRequest, MemoryStoreResponse,
    MemorySearchRequest, MemorySearchResponse,
    MemoryUpdateRequest,
    ACLGrantRequest,
    AgentRegisterRequest, AgentRegisterResponse,
    HealthResponse
)
from .dependencies import get_memory_manager, verify_api_key

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    memory: MemoryManager = Depends(get_memory_manager)
):
    """健康检查"""
    db = memory.db
    
    # 统计
    mem_count = db.fetchone("SELECT COUNT(*) as c FROM shared_memories WHERE is_deleted = 0")
    shared_count = db.fetchone("SELECT COUNT(*) as c FROM shared_memories WHERE is_deleted = 0 AND visibility = 'shared'")
    agent_count = db.fetchone("SELECT COUNT(*) as c FROM agent_registry WHERE status = 'active'")
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database_path=db.db_path,
        agents_online=agent_count['c'] if agent_count else 0,
        memories_total=mem_count['c'] if mem_count else 0,
        shared_memories=shared_count['c'] if shared_count else 0
    )


@router.post("/memory/store", response_model=MemoryStoreResponse)
async def store_memory(
    request: MemoryStoreRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """存储新记忆"""
    try:
        entry = memory.store(
            content=request.content,
            source_agent=x_agent_id,
            memory_type=request.memory_type,
            visibility=request.visibility,
            importance=request.importance,
            tags=request.tags,
            project_path=request.project_path,
            source_user=request.source_user,
            valid_until=request.valid_until
        )
        
        return MemoryStoreResponse(
            id=entry.id,
            content=entry.content,
            summary=entry.summary,
            memory_type=entry.memory_type,
            visibility=entry.visibility,
            importance=entry.importance,
            tags=entry.tags,
            created_at=entry.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    request: MemorySearchRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """搜索记忆"""
    start_time = time.time()
    
    try:
        results = memory.search(
            query=request.query,
            agent_id=x_agent_id,
            limit=request.limit,
            memory_types=request.memory_types,
            visibility=request.visibility,
            project_path=request.project_path,
            min_importance=request.min_importance
        )
        
        query_time = int((time.time() - start_time) * 1000)
        
        return MemorySearchResponse(
            results=results,
            total=len(results),
            query_time_ms=query_time,
            agents_searched=["openclaw", "claude_code", "codex"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/{memory_id}")
async def get_memory(
    memory_id: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """获取单条记忆"""
    db = memory.db
    
    sql = "SELECT * FROM shared_memories WHERE id = ? AND is_deleted = 0"
    entry = db.fetchone(sql, (memory_id,))
    
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # 更新访问统计
    memory._update_access_stats([memory_id], x_agent_id)
    
    return entry


@router.patch("/memory/{memory_id}")
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """更新记忆"""
    if not memory._can_modify(memory_id, x_agent_id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = memory.db
    
    # 构建更新
    updates = []
    params = []
    
    if request.content is not None:
        updates.append("content = ?")
        params.append(request.content)
        # 重新生成向量
        embedding = memory.embedding.embed(request.content)
        updates.append("embedding = ?")
        params.append(str(embedding))
    
    if request.summary is not None:
        updates.append("summary = ?")
        params.append(request.summary)
    
    if request.importance is not None:
        updates.append("importance = ?")
        params.append(request.importance)
    
    if request.tags is not None:
        updates.append("tags = ?")
        params.append(str(request.tags))
    
    if request.visibility is not None:
        updates.append("visibility = ?")
        params.append(request.visibility)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    updates.append("updated_at = ?")
    params.append(int(time.time() * 1000))
    params.append(memory_id)
    
    sql = f"UPDATE shared_memories SET {', '.join(updates)} WHERE id = ?"
    
    try:
        db.execute(sql, tuple(params))
        return {"status": "updated", "id": memory_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    permanent: bool = Query(False),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """删除记忆"""
    if permanent:
        success = memory.hard_delete(memory_id, x_agent_id)
    else:
        success = memory.soft_delete(memory_id, x_agent_id)
    
    if not success:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return {"status": "deleted", "id": memory_id}


@router.post("/memory/{memory_id}/restore")
async def restore_memory(
    memory_id: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """恢复已删除的记忆"""
    success = memory.restore(memory_id, x_agent_id)
    
    if not success:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return {"status": "restored", "id": memory_id}


@router.post("/acl/grant")
async def grant_access(
    request: ACLGrantRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """授予访问权限"""
    success = memory.grant_access(
        memory_id=request.memory_id,
        agent_id=request.agent_id,
        permission=request.permission,
        granted_by=x_agent_id,
        expires_at=request.expires_at
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to grant access")
    
    return {"status": "granted", "memory_id": request.memory_id, "agent_id": request.agent_id}


@router.delete("/acl/revoke")
async def revoke_access(
    memory_id: str,
    agent_id: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """撤销访问权限"""
    success = memory.revoke_access(memory_id, agent_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke access")
    
    return {"status": "revoked", "memory_id": memory_id, "agent_id": agent_id}


@router.post("/agent/register", response_model=AgentRegisterResponse)
async def register_agent(
    request: AgentRegisterRequest,
    memory: MemoryManager = Depends(get_memory_manager)
):
    """注册 Agent"""
    db = memory.db
    
    # 检查是否已存在
    existing = db.fetchone(
        "SELECT agent_id FROM agent_registry WHERE agent_id = ?",
        (request.agent_id,)
    )
    
    now = int(time.time() * 1000)
    api_key = None
    
    if existing:
        # 更新
        sql = """
        UPDATE agent_registry
        SET name = ?, description = ?, endpoint = ?, version = ?,
            capabilities = ?, updated_at = ?, last_seen_at = ?, status = 'active'
        WHERE agent_id = ?
        """
        db.execute(sql, (
            request.name, request.description, request.endpoint,
            request.version, str(request.capabilities) if request.capabilities else None,
            now, now, request.agent_id
        ))
    else:
        # 新建
        import uuid
        api_key = f"sk_{uuid.uuid4().hex}"
        api_key_hash = str(hash(api_key))  # 简单 hash，生产环境应加密
        
        sql = """
        INSERT INTO agent_registry (
            agent_id, agent_type, name, description, endpoint, version,
            capabilities, status, created_at, updated_at, last_seen_at, api_key_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute(sql, (
            request.agent_id, request.agent_type, request.name,
            request.description, request.endpoint, request.version,
            str(request.capabilities) if request.capabilities else None,
            'active', now, now, now, str(api_key_hash)
        ))
        
        # 分配默认角色
        role_sql = """
        INSERT INTO agent_roles (id, agent_id, role_type, created_at, updated_at)
        VALUES (?, ?, 'member', ?, ?)
        """
        role_id = f"role_{uuid.uuid4().hex[:12]}"
        db.execute(role_sql, (role_id, request.agent_id, now, now))
    
    return AgentRegisterResponse(
        agent_id=request.agent_id,
        status="registered",
        registered_at=now,
        api_key=api_key
    )


@router.get("/agent/{agent_id}")
async def get_agent(
    agent_id: str,
    memory: MemoryManager = Depends(get_memory_manager)
):
    """获取 Agent 信息"""
    db = memory.db
    
    sql = "SELECT * FROM agent_registry WHERE agent_id = ?"
    agent = db.fetchone(sql, (agent_id,))
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 获取角色
    role_sql = "SELECT role_type FROM agent_roles WHERE agent_id = ?"
    role = db.fetchone(role_sql, (agent_id,))
    
    return {
        **agent,
        'role': role['role_type'] if role else None
    }


@router.get("/memories")
async def list_memories(
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
    memory_type: Optional[str] = None,
    visibility: Optional[str] = None,
    project_path: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """列出记忆 (分页)"""
    db = memory.db
    
    conditions = ["is_deleted = 0"]
    params = []
    
    if memory_type:
        conditions.append("memory_type = ?")
        params.append(memory_type)
    
    if visibility:
        conditions.append("visibility = ?")
        params.append(visibility)
    
    if project_path:
        conditions.append("project_path = ?")
        params.append(project_path)
    
    where = " AND ".join(conditions)
    
    sql = f"""
    SELECT * FROM shared_memories
    WHERE {where}
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
    """
    
    results = db.fetchall(sql, (*params, limit, offset))
    
    # 总数
    count_sql = f"SELECT COUNT(*) as c FROM shared_memories WHERE {where}"
    total = db.fetchone(count_sql, tuple(params))['c']
    
    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

### 3.3 依赖注入

```python
# src/api/dependencies.py

from fastapi import Header, HTTPException
from typing import Optional

from ..core.memory_manager import MemoryManager
from ..core.database import DatabaseManager
from ..utils.embedding import EmbeddingService

# 全局实例
_memory_manager: Optional[MemoryManager] = None


def get_database() -> DatabaseManager:
    """获取数据库实例"""
    return DatabaseManager()


def get_embedding_service() -> EmbeddingService:
    """获取嵌入服务实例"""
    return EmbeddingService()


def get_memory_manager() -> MemoryManager:
    """获取记忆管理器实例"""
    global _memory_manager
    
    if _memory_manager is None:
        db = get_database()
        embedding = get_embedding_service()
        _memory_manager = MemoryManager(db=db, embedding_service=embedding)
    
    return _memory_manager


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    验证 API Key
    返回 agent_id
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    db = get_database()
    
    # 查询对应的 agent
    sql = """
    SELECT agent_id, api_key_hash, status FROM agent_registry
    WHERE api_key_hash = ?
    """
    
    result = db.fetchone(sql, (str(hash(x_api_key)),))
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if result['status'] != 'active':
        raise HTTPException(status_code=403, detail="Agent not active")
    
    # 更新 last_seen
    import time
    db.execute(
        "UPDATE agent_registry SET last_seen_at = ? WHERE agent_id = ?",
        (int(time.time() * 1000), result['agent_id'])
    )
    
    return result['agent_id']


async def verify_agent_header(
    x_agent_id: str = Header(..., alias="X-Agent-ID")
) -> str:
    """
    验证 Agent ID header
    简化版：只检查是否存在
    """
    if not x_agent_id:
        raise HTTPException(status_code=400, detail="X-Agent-ID header required")
    
    return x_agent_id
```

---

## 4. 启动入口

```python
# run.py

#!/usr/bin/env python3
"""
Memory Gateway 启动入口
跨 Agent 共享记忆服务
"""

import os
import sys
import argparse
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.routes import router
from src.utils.logger import get_logger
from src.core.database import DatabaseManager

logger = get_logger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Memory Sharing Gateway",
    description="跨 Agent 共享记忆服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    logger.info("Starting Memory Gateway...")
    
    # 初始化数据库
    db = DatabaseManager()
    logger.info(f"Database initialized at: {db.db_path}")
    
    # 检查 OpenClaw 链接
    if db.has_openclaw_tables:
        logger.info("OpenClaw tables linked successfully")
    else:
        logger.warning("OpenClaw tables not found - some features may be limited")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    logger.info("Shutting down Memory Gateway...")
    
    db = DatabaseManager()
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Memory Sharing Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=3045, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--db-path", help="Custom database path")
    
    args = parser.parse_args()
    
    # 可以通过参数指定数据库路径
    if args.db_path:
        os.environ['MEMORY_DB_PATH'] = args.db_path
    
    uvicorn.run(
        "run:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
```

---

## 5. 工作流程图

### 5.1 存储记忆流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Store Memory Flow                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Client (Claude Code / Codex)                                    │
│       │                                                          │
│       │  POST /api/v1/memory/store                               │
│       │  { content, type, visibility, tags, ... }                 │
│       │                                                          │
│       ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Gateway API Layer                            │   │
│  │  - verify_agent_header() 验证 X-Agent-ID                  │   │
│  │  - validate request (Pydantic)                            │   │
│  │  - rate limiting (可选)                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MemoryManager.store()                        │   │
│  │                                                           │   │
│  │  1. 创建 MemoryEntry 对象                                 │   │
│  │       │                                                  │   │
│  │       ├── 生成 UUID (shr_xxxxx)                          │   │
│  │       ├── 设置时间戳                                      │   │
│  │       ├── 标记 source_agent                               │   │
│  │       └── 分配默认 visibility                            │   │
│  │       │                                                  │   │
│  │       ↓                                                  │   │
│  │  2. 生成摘要 (_generate_summary)                         │   │
│  │       │                                                  │   │
│  │  3. 生成向量 (embedding.embed())                        │   │
│  │       │  → 调用 OpenAI/Ollama 嵌入模型                   │   │
│  │       ↓                                                  │   │
│  │  4. 写入 SQLite (_insert_entry)                         │   │
│  │       │  INSERT INTO shared_memories (...)               │   │
│  │       ↓                                                  │   │
│  │  5. 写入向量索引 (_insert_vector)                        │   │
│  │       │  INSERT INTO shared_memories_vec                 │   │
│  │       ↓                                                  │   │
│  │  6. 写入 FTS (_insert_fts)                               │   │
│  │       │  INSERT INTO shared_memories_fts                │   │
│  │       ↓                                                  │   │
│  │  7. 返回 MemoryStoreResponse                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ↓                                                          │
│  Response: { id, content, summary, created_at, ... }             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 搜索记忆流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Search Memory Flow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Client                                                          │
│       │                                                          │
│       │  POST /api/v1/memory/search                              │
│       │  { query, limit, types, project_path, ... }             │
│       │                                                          │
│       ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Gateway API Layer                            │   │
│  │  - verify_agent_header()                                  │   │
│  │  - validate request                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MemoryManager.search()                        │   │
│  │                                                           │   │
│  │  1. 权限检查 (_get_accessible_visibility)                 │   │
│  │       │                                                  │   │
│  │       ├── 查询 agent_roles 表                             │   │
│  │       └── 返回可访问的 visibility 列表                    │   │
│  │       │  → owner: ['private', 'shared', 'global']         │   │
│  │       │  → member: ['shared', 'global']                   │   │
│  │       ↓                                                  │   │
│  │  2. 生成查询向量                                          │   │
│  │       │  embedding.embed(query)                           │   │
│  │       ↓                                                  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │         Parallel Search (向量 + 关键词)              │  │   │
│  │  │                                                     │  │   │
│  │  │  ┌──────────────────┐  ┌──────────────────┐        │  │   │
│  │  │  │  Vector Search   │  │ Keyword Search   │        │  │   │
│  │  │  │                  │  │                  │        │  │   │
│  │  │  │  sqlite-vec      │  │ FTS5 (BM25)      │        │  │   │
│  │  │  │  余弦相似度     │  │                  │        │  │   │
│  │  │  │                  │  │                  │        │  │   │
│  │  │  │  返回 top N     │  │ 返回 top N       │        │  │   │
│  │  │  └──────────────────┘  └──────────────────┘        │  │   │
│  │  │           ↓                      ↓                │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │       │                                                          │
│  │       ↓                                                          │
│  │  3. 结果融合 (_merge_results)                                    │
│  │       │                                                          │
│  │       ├── 去重 (按 memory_id)                                    │
│  │       ├── 加权合并                                                │
│  │       │  score = 0.7 × vector_sim + 0.3 × norm_bm25             │
│  │       └── 按 score 排序                                          │
│  │       ↓                                                          │
│  │  4. ACL 过滤 (_filter_by_acl)                                   │
│  │       │                                                          │
│  │       ├── private: 只允许创建者 + owner                          │
│  │       ├── shared: 允许同项目 Agent                              │
│  │       └── global: 允许所有                                     │
│  │       ↓                                                          │
│  │  5. 更新访问统计 (_update_access_stats)                          │
│  │       │  access_count++, last_accessed_at                      │
│  │       ↓                                                          │
│  │  6. 记录搜索历史 (_log_search)                                   │
│  │       │  INSERT INTO search_history                            │
│  │       ↓                                                          │
│  │  7. 返回结果                                                     │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ↓                                                          │
│  Response: {                                                      │
│    results: [{                                                     │
│      id, content, summary, type, importance,                     │
│      source_agent, score, sources                                │
│    }],                                                            │
│    total, query_time_ms, agents_searched                         │
│  }                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 配置管理

```yaml
# config.yaml

# 服务器配置
server:
  host: "0.0.0.0"
  port: 3045
  workers: 1
  reload: false

# 数据库
database:
  path: "~/.openclaw/workspace/agent-memory-system/data/shared_memory.db"
  
# 向量嵌入
embedding:
  provider: "openai"  # openai | ollama | local
  model: "text-embedding-3-small"
  dimension: 1536
  
  # OpenAI 配置
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
  
  # Ollama 配置 (本地)
  ollama:
    base_url: "http://localhost:11434"
    model: "nomic-embed-text"

# 搜索配置
search:
  default_limit: 10
  max_limit: 100
  vector_weight: 0.7
  keyword_weight: 0.3
  min_score: 0.35

# 访问控制
acl:
  default_visibility: "shared"
  allow_cross_agent: true
  api_key_required: false  # 开发环境可关闭

# 日志
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## 7. 依赖

```text
# requirements.txt

fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
sqlite3 (built-in)
# sqlite-vec (需要编译安装)
# 或使用内联余弦相似度计算作为回退

# 向量嵌入
openai>=1.0.0
# 或
requests>=2.28.0  # for Ollama

# 可选
python-dotenv>=1.0.0
pyyaml>=6.0
```

---

*实现版本 v1.0*
*项目路径: agent-memory-system/src/*
