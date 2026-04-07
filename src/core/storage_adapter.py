# -*- coding: utf-8 -*-
"""
Storage Adapter - 存储适配器基类
支持 MySQL 5.7+ / MySQL 8.0+ / SQLite
"""

import json
import time
import uuid
import sqlite3
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from .models import Memory, MemoryType, Visibility, Source


class StorageAdapter(ABC):
    """存储适配器基类"""
    
    @abstractmethod
    def insert_memory(self, memory: Memory) -> Memory:
        """插入记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str, include_deleted: bool = False) -> Optional[Memory]:
        """获取单条记忆"""
        pass
    
    @abstractmethod
    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str, hard: bool = False) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def search_memories(
        self,
        query: str,
        memory_type: str = None,
        project_path: str = None,
        visibility: str = None,
        limit: int = 10,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Tuple[Memory, float]]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    def list_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        source: str = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Memory]:
        """列出记忆"""
        pass
    
    @abstractmethod
    def count_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        include_deleted: bool = False
    ) -> int:
        """统计数量"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭连接"""
        pass
    
    # ============================================================
    # 工具方法
    # ============================================================
    
    @staticmethod
    def generate_id() -> str:
        """生成记忆 ID"""
        return f"mem_{uuid.uuid4().hex[:10]}"
    
    @staticmethod
    def now_ms() -> int:
        """当前时间戳(毫秒)"""
        return int(time.time() * 1000)
    
    @staticmethod
    def serialize_tags(tags: Any) -> str:
        """序列化标签"""
        if tags is None:
            return '[]'
        if isinstance(tags, str):
            return tags
        if isinstance(tags, (list, tuple)):
            return json.dumps(tags, ensure_ascii=False)
        return '[]'
    
    @staticmethod
    def deserialize_tags(text: str) -> List[str]:
        """反序列化标签"""
        if not text:
            return []
        if isinstance(text, list):
            return text
        try:
            return json.loads(text)
        except:
            return []


class SQLiteAdapter(StorageAdapter):
    """
    SQLite 适配器
    用于本地存储或云端文件共享 (SMB/NFS)
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = self._get_connection()
        
        # WAL 模式提升并发
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        
        # 创建表
        conn.executescript("""
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
            
            CREATE TABLE IF NOT EXISTS acl (
                memory_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                permission TEXT NOT NULL DEFAULT 'read',
                granted_by TEXT NOT NULL,
                granted_at INTEGER NOT NULL,
                expires_at INTEGER,
                PRIMARY KEY (memory_id, agent_id)
            );
            
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
        """)
        conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_memory(self, memory: Memory) -> Memory:
        sql = """
        INSERT INTO memories (
            id, content, summary, type, visibility,
            source, source_agent, project_path, importance,
            tags, created_at, updated_at, is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self._cursor() as cursor:
            cursor.execute(sql, (
                memory.id,
                memory.content,
                memory.summary,
                memory.type,
                memory.visibility,
                memory.source,
                memory.source_agent,
                memory.project_path,
                memory.importance,
                self.serialize_tags(memory.tags),
                memory.created_at,
                memory.updated_at,
                1 if memory.is_deleted else 0
            ))
        
        return memory
    
    def get_memory(self, memory_id: str, include_deleted: bool = False) -> Optional[Memory]:
        sql = "SELECT * FROM memories WHERE id = ?"
        if not include_deleted:
            sql += " AND is_deleted = 0"
        
        with self._cursor() as cursor:
            cursor.execute(sql, (memory_id,))
            row = cursor.fetchone()
        
        if row:
            return self._row_to_memory(row)
        return None
    
    def update_memory(self, memory: Memory) -> bool:
        sql = """
        UPDATE memories SET
            content = ?, summary = ?, type = ?, visibility = ?,
            project_path = ?, importance = ?, tags = ?,
            updated_at = ?, is_deleted = ?
        WHERE id = ?
        """
        
        with self._cursor() as cursor:
            cursor.execute(sql, (
                memory.content,
                memory.summary,
                memory.type,
                memory.visibility,
                memory.project_path,
                memory.importance,
                self.serialize_tags(memory.tags),
                memory.updated_at,
                1 if memory.is_deleted else 0,
                memory.id
            ))
            return cursor.rowcount > 0
    
    def delete_memory(self, memory_id: str, hard: bool = False) -> bool:
        if hard:
            with self._cursor() as cursor:
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                return cursor.rowcount > 0
        else:
            return self.update_memory(
                Memory(
                    id=memory_id,
                    content="",
                    is_deleted=True,
                    updated_at=self.now_ms()
                )
            )
    
    def search_memories(
        self,
        query: str,
        memory_type: str = None,
        project_path: str = None,
        visibility: str = None,
        limit: int = 10,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Tuple[Memory, float]]:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if query:
            conditions.append("(content LIKE ? OR tags LIKE ? OR summary LIKE ?)")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        if visibility:
            conditions.append("visibility = ?")
            params.append(visibility)
        
        where = " AND ".join(conditions)
        
        sql = f"""
        SELECT * FROM memories
        WHERE {where}
        ORDER BY importance DESC, created_at DESC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            memory = self._row_to_memory(row)
            score = self._calc_score(memory, query)
            results.append((memory, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def list_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        source: str = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Memory]:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        where = " AND ".join(conditions)
        
        sql = f"""
        SELECT * FROM memories
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def count_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        include_deleted: bool = False
    ) -> int:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        where = " AND ".join(conditions)
        
        with self._cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as c FROM memories WHERE {where}", tuple(params))
            row = cursor.fetchone()
        
        return row['c'] if row else 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN type = 'project' THEN 1 ELSE 0 END) as projects,
                    SUM(CASE WHEN type = 'preference' THEN 1 ELSE 0 END) as preferences,
                    SUM(CASE WHEN type = 'knowledge' THEN 1 ELSE 0 END) as knowledge,
                    SUM(CASE WHEN type = 'general' THEN 1 ELSE 0 END) as general,
                    SUM(CASE WHEN type = 'team' THEN 1 ELSE 0 END) as team
                FROM memories WHERE is_deleted = 0
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Row 转 Memory"""
        return Memory(
            id=row['id'],
            content=row['content'],
            summary=row['summary'],
            type=row['type'],
            visibility=row['visibility'],
            source=row['source'],
            source_agent=row['source_agent'],
            project_path=row['project_path'],
            importance=row['importance'],
            tags=self.deserialize_tags(row['tags']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            is_deleted=bool(row['is_deleted'])
        )
    
    def _calc_score(self, memory: Memory, query: str) -> float:
        """计算相关性分数"""
        if not query:
            return memory.importance / 10.0
        
        score = 0.0
        query_lower = query.lower()
        content_lower = memory.content.lower()
        
        # 精确包含
        if query_lower in content_lower:
            score += 0.5
        
        # 词匹配
        query_words = query_lower.split()
        content_words = content_lower.split()
        matches = sum(1 for w in query_words if w in content_words)
        score += matches / max(len(query_words), 1) * 0.3
        
        # 标签匹配
        for tag in memory.tags:
            if query_lower in tag.lower():
                score += 0.2
        
        # 重要性
        score += memory.importance / 10.0 * 0.2
        
        return min(1.0, max(0.0, score))


class MySQLAdapter(StorageAdapter):
    """
    MySQL 适配器
    支持 MySQL 5.7 和 8.0+
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._pool = None
        self._version = None
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池"""
        try:
            import pymysql
            from dbutils.pooled_db import PooledDB
        except ImportError:
            raise ImportError(
                "pymysql and dbutils are required for MySQL. "
                "Install: pip install pymysql dbutils"
            )
        
        # 检测版本
        conn = pymysql.connect(
            host=self.config['host'],
            port=self.config.get('port', 3306),
            user=self.config['user'],
            password=self.config['password'],
            charset=self.config.get('charset', 'utf8mb4')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version_str = cursor.fetchone()[0]
        conn.close()
        
        # 提取主版本号
        self._version = float(version_str.split('.')[0])
        
        # 创建连接池
        self._pool = PooledDB(
            creator=pymysql,
            maxconnections=self.config.get('pool', {}).get('max_size', 20),
            mincached=self.config.get('pool', {}).get('min_size', 5),
            blocking=True,
            host=self.config['host'],
            port=self.config.get('port', 3306),
            database=self.config['database'],
            user=self.config['user'],
            password=self.config['password'],
            charset=self.config.get('charset', 'utf8mb4'),
            connect_timeout=self.config.get('timeout', {}).get('connect', 10),
            read_timeout=self.config.get('timeout', {}).get('read', 30),
            write_timeout=self.config.get('timeout', {}).get('write', 30),
        )
    
    @property
    def is_mysql80(self) -> bool:
        """是否是 MySQL 8.0+"""
        return self._version >= 8.0
    
    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器"""
        conn = self._pool.connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def insert_memory(self, memory: Memory) -> Memory:
        # MySQL 5.7 用 VARCHAR 存 JSON
        sql = """
        INSERT INTO memories (
            id, content, summary, type, visibility,
            source, source_agent, project_path, importance,
            tags, created_at, updated_at, is_deleted,
            share_title, md_content, notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self._cursor() as cursor:
            cursor.execute(sql, (
                memory.id,
                memory.content,
                memory.summary,
                memory.type,
                memory.visibility,
                memory.source,
                memory.source_agent,
                memory.project_path,
                memory.importance,
                self.serialize_tags(memory.tags),
                memory.created_at,
                memory.updated_at,
                1 if memory.is_deleted else 0,
                memory.share_title,
                memory.md_content,
                memory.notes
            ))
        
        return memory
    
    def get_memory(self, memory_id: str, include_deleted: bool = False) -> Optional[Memory]:
        sql = "SELECT * FROM memories WHERE id = %s"
        if not include_deleted:
            sql += " AND is_deleted = 0"
        
        with self._cursor() as cursor:
            cursor.execute(sql, (memory_id,))
            row = cursor.fetchone()
        
        if row:
            return self._row_to_memory(row)
        return None
    
    def update_memory(self, memory: Memory) -> bool:
        sql = """
        UPDATE memories SET
            content = %s, summary = %s, type = %s, visibility = %s,
            project_path = %s, importance = %s, tags = %s,
            updated_at = %s, is_deleted = %s,
            share_title = %s, md_content = %s, notes = %s
        WHERE id = %s
        """
        
        with self._cursor() as cursor:
            cursor.execute(sql, (
                memory.content,
                memory.summary,
                memory.type,
                memory.visibility,
                memory.project_path,
                memory.importance,
                self.serialize_tags(memory.tags),
                memory.updated_at,
                1 if memory.is_deleted else 0,
                memory.share_title,
                memory.md_content,
                memory.notes,
                memory.id
            ))
            return cursor.rowcount > 0
    
    def delete_memory(self, memory_id: str, hard: bool = False) -> bool:
        if hard:
            with self._cursor() as cursor:
                cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
                return cursor.rowcount > 0
        else:
            # 软删除
            with self._cursor() as cursor:
                cursor.execute(
                    "UPDATE memories SET is_deleted = 1, updated_at = %s WHERE id = %s",
                    (self.now_ms(), memory_id)
                )
                return cursor.rowcount > 0
    
    def search_memories(
        self,
        query: str,
        memory_type: str = None,
        project_path: str = None,
        visibility: str = None,
        limit: int = 10,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Tuple[Memory, float]]:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if query:
            # MySQL 5.7 不支持 FULLTEXT 在 TEXT 上，用 LIKE
            # MySQL 8.0+ 可以用 MATCH...AGAINST，但这里统一用 LIKE 保证兼容
            conditions.append("(content LIKE %s OR tags LIKE %s OR summary LIKE %s)")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])
        
        if memory_type:
            conditions.append("type = %s")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = %s")
            params.append(project_path)
        
        if visibility:
            conditions.append("visibility = %s")
            params.append(visibility)
        
        where = " AND ".join(conditions)
        
        sql = f"""
        SELECT * FROM memories
        WHERE {where}
        ORDER BY importance DESC, created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            memory = self._row_to_memory(row)
            score = self._calc_score(memory, query)
            results.append((memory, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def list_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        source: str = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Memory]:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if memory_type:
            conditions.append("type = %s")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = %s")
            params.append(project_path)
        
        if source:
            conditions.append("source = %s")
            params.append(source)
        
        where = " AND ".join(conditions)
        
        sql = f"""
        SELECT * FROM memories
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def count_memories(
        self,
        memory_type: str = None,
        project_path: str = None,
        include_deleted: bool = False
    ) -> int:
        conditions = ["is_deleted = 0" if not include_deleted else "1=1"]
        params = []
        
        if memory_type:
            conditions.append("type = %s")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = %s")
            params.append(project_path)
        
        where = " AND ".join(conditions)
        
        with self._cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as c FROM memories WHERE {where}", tuple(params))
            row = cursor.fetchone()
        
        return row[0] if row else 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(type = 'project') as projects,
                    SUM(type = 'preference') as preferences,
                    SUM(type = 'knowledge') as knowledge,
                    SUM(type = 'general') as general,
                    SUM(type = 'team') as team
                FROM memories WHERE is_deleted = 0
            """)
            row = cursor.fetchone()
            
            if row:
                return {
                    'total': row[0] or 0,
                    'projects': row[1] or 0,
                    'preferences': row[2] or 0,
                    'knowledge': row[3] or 0,
                    'general': row[4] or 0,
                    'team': row[5] or 0
                }
            return {}
    
    def close(self):
        if self._pool:
            self._pool.close()
            self._pool = None
    
    def _row_to_memory(self, row: tuple) -> Memory:
        """Row 转 Memory"""
        # 转换 Decimal 为 float
        def to_float(v):
            if v is None:
                return 5.0
            try:
                from decimal import Decimal
                if isinstance(v, Decimal):
                    return float(v)
            except ImportError:
                pass
            return float(v) if isinstance(v, (int, float)) else v
        
        # 转换所有可能的 Decimal 字段
        importance = to_float(row[8])
        created_at = int(row[10]) if row[10] else row[10]
        updated_at = int(row[11]) if row[11] else row[11]
        
        return Memory(
            id=str(row[0]) if row[0] else '',
            content=str(row[1]) if row[1] else '',
            summary=str(row[2]) if row[2] else None,
            type=str(row[3]) if row[3] else 'general',
            visibility=str(row[4]) if row[4] else 'shared',
            source=str(row[5]) if row[5] else 'cli',
            source_agent=str(row[6]) if row[6] else None,
            project_path=str(row[7]) if row[7] else None,
            importance=importance,
            tags=self.deserialize_tags(row[9]),
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=bool(row[12]),
            # 经验分享专用字段
            share_title=str(row[13]) if len(row) > 13 and row[13] else None,
            md_content=str(row[14]) if len(row) > 14 and row[14] else None,
            notes=str(row[15]) if len(row) > 15 and row[15] else None
        )
    
    def _calc_score(self, memory: Memory, query: str) -> float:
        """计算相关性分数"""
        if not query:
            return memory.importance / 10.0
        
        score = 0.0
        query_lower = query.lower()
        content_lower = memory.content.lower()
        
        if query_lower in content_lower:
            score += 0.5
        
        query_words = query_lower.split()
        content_words = content_lower.split()
        matches = sum(1 for w in query_words if w in content_words)
        score += matches / max(len(query_words), 1) * 0.3
        
        for tag in memory.tags:
            if query_lower in tag.lower():
                score += 0.2
        
        score += memory.importance / 10.0 * 0.2
        
        return min(1.0, max(0.0, score))


def create_storage(config: Dict[str, Any]) -> StorageAdapter:
    """
    根据配置创建合适的存储适配器
    
    Args:
        config: 配置字典，至少包含:
            - type: 'mysql' 或 'sqlite'
            - mysql: host, port, user, password, database
            - sqlite: path
    """
    storage_type = config.get('type', 'sqlite')
    
    if storage_type == 'mysql':
        return MySQLAdapter(config)
    else:
        # 默认 SQLite
        db_path = config.get('path', '~/.memory/memory.db')
        # 处理 ~ 路径
        if db_path.startswith('~'):
            import os
            db_path = os.path.expanduser(db_path)
        return SQLiteAdapter(db_path)
