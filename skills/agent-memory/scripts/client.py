# -*- coding: utf-8 -*-
"""
Agent Memory Skill - MySQL Client
使用 PyMySQL 直接连接 MySQL，经验内容存储在 content 字段（MD格式）
"""

import os
import sys
import json
import time
import uuid
import hashlib
from typing import Optional, List, Dict, Any

# 尝试导入 PyMySQL
try:
    import pymysql
    from pymysql.cursors import DictCursor
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

from .config import get_config, require_config, ConfigurationError


class DatabaseError(Exception):
    """数据库错误异常"""
    pass


class ExperienceClient:
    """
    经验客户端
    
    用于：
    - 分享经验到云端
    - 查询云端经验
    - 获取经验详情
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self._connection: Optional[pymysql.Connection] = None
    
    def _get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        if not PYMYSQL_AVAILABLE:
            raise DatabaseError(
                "PyMySQL 未安装。请运行: pip install pymysql\n"
                "或设置环境变量使用 SQLite 兼容模式"
            )
        
        if self._connection is None or not self._connection.open:
            try:
                self._connection = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    charset=self.config.charset,
                    cursorclass=DictCursor,
                    connect_timeout=10,
                    read_timeout=30,
                    write_timeout=30,
                )
            except pymysql.Error as e:
                raise DatabaseError(f"数据库连接失败: {e}")
        
        return self._connection
    
    def _close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None
    
    def _ensure_experience_code(self, domain: str, primary_tag: str) -> str:
        """
        生成唯一经验代码
        
        格式: EXP-{DOMAIN}-{TAG}-{SEQ:4}
        例如: EXP-BACKEND-FASTAPI-0001
        """
        domain = domain.upper()[:10]
        tag = primary_tag.upper()[:10]
        
        conn = self._get_connection()
        with conn.cursor() as cursor:
            # 获取下一个序号
            cursor.execute(
                """INSERT INTO experience_sequences (domain, tag, current_seq)
                   VALUES (%s, %s, 1)
                   ON DUPLICATE KEY UPDATE current_seq = current_seq + 1""",
                (domain, tag)
            )
            conn.commit()
            
            cursor.execute(
                "SELECT current_seq FROM experience_sequences WHERE domain = %s AND tag = %s",
                (domain, tag)
            )
            result = cursor.fetchone()
            seq = result['current_seq'] if result else 1
        
        return f"EXP-{domain}-{tag}-{seq:04d}"
    
    def share_experience(
        self,
        title: str,
        content: str,
        summary: str = "",
        tags: List[str] = None,
        domain: str = "GENERAL",
        importance: float = 5.0,
        level: str = "intermediate",
        author_id: str = "openclaw",
        author_name: str = None,
        author_type: str = "openclaw",
        visibility: str = "shared",
        status: str = "published",
    ) -> Dict[str, Any]:
        """
        分享经验到云端
        
        Args:
            title: 经验标题
            content: MD格式正文（核心内容）
            summary: 一句话摘要
            tags: 标签列表
            domain: 领域
            importance: 重要性 1-10
            level: 难度级别
            author_id: 作者ID
            author_name: 作者显示名
            author_type: 来源类型
            visibility: 可见性
            status: 状态
        
        Returns:
            经验元数据字典，包含 id 和 code
        """
        require_config()
        
        if tags is None:
            tags = []
        
        # 生成唯一 ID
        memory_id = f"mem_{uuid.uuid4().hex[:10]}"
        
        # 生成经验代码
        primary_tag = tags[0].upper().replace("-", "_") if tags else "GENERAL"
        code = self._ensure_experience_code(domain, primary_tag)
        
        # 计算文件哈希
        file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # 时间戳
        now = int(time.time() * 1000)
        
        conn = self._get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO experiences 
                   (id, code, title, summary, content, domain, tags, importance, level,
                    file_hash, author_id, author_name, author_type, visibility, status,
                    quality_score, usage_count, helpful_count, version, language_code,
                    created_at, updated_at, published_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    memory_id, code, title, summary, content, domain,
                    json.dumps(tags, ensure_ascii=False),
                    importance, level, file_hash,
                    author_id, author_name, author_type,
                    visibility, status,
                    5.0, 0, 0, 1, "zh",
                    now, now, now
                )
            )
            conn.commit()
        
        return {
            "id": memory_id,
            "code": code,
            "title": title,
            "summary": summary,
            "domain": domain,
            "tags": tags,
            "importance": importance,
            "author_id": author_id,
            "created_at": now,
        }
    
    def search_experiences(
        self,
        query: str,
        domain: str = None,
        tags: List[str] = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        搜索云端经验
        
        Args:
            query: 搜索关键词
            domain: 领域过滤
            tags: 标签过滤
            limit: 返回数量
            min_importance: 最低重要性
        
        Returns:
            经验列表
        """
        require_config()
        
        conn = self._get_connection()
        
        # 构建查询
        sql = """
            SELECT id, code, title, summary, domain, tags, importance,
                   author_id, author_name, level, usage_count, helpful_count,
                   created_at, published_at
            FROM experiences
            WHERE status = 'published' AND visibility IN ('shared', 'global')
        """
        params = []
        
        if query:
            sql += " AND (title LIKE %s OR summary LIKE %s OR content LIKE %s)"
            like_query = f"%{query}%"
            params.extend([like_query, like_query, like_query])
        
        if domain:
            sql += " AND domain = %s"
            params.append(domain)
        
        if tags:
            for tag in tags:
                sql += " AND JSON_CONTAINS(tags, %s)"
                params.append(json.dumps(tag))
        
        if min_importance > 0:
            sql += " AND importance >= %s"
            params.append(min_importance)
        
        sql += " ORDER BY importance DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
        
        # 处理结果
        for exp in results:
            if exp.get('tags') and isinstance(exp['tags'], str):
                try:
                    exp['tags'] = json.loads(exp['tags'])
                except:
                    exp['tags'] = []
        
        return results
    
    def get_experience(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单条经验详情
        
        Args:
            code: 经验代码，如 EXP-BACKEND-FASTAPI-0001
        
        Returns:
            经验详情（包含 content 字段），未找到返回 None
        """
        require_config()
        
        conn = self._get_connection()
        
        with conn.cursor() as cursor:
            # 查询经验
            cursor.execute(
                """SELECT * FROM experiences WHERE code = %s""",
                (code,)
            )
            exp = cursor.fetchone()
        
        if not exp:
            return None
        
        # 处理 tags
        if exp.get('tags') and isinstance(exp['tags'], str):
            try:
                exp['tags'] = json.loads(exp['tags'])
            except:
                exp['tags'] = []
        
        # 处理 related_codes
        if exp.get('related_codes') and isinstance(exp['related_codes'], str):
            try:
                exp['related_codes'] = json.loads(exp['related_codes'])
            except:
                exp['related_codes'] = []
        
        # 更新查阅次数
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE experiences SET usage_count = usage_count + 1 WHERE code = %s",
                (code,)
            )
            conn.commit()
        
        return exp
    
    def list_experiences(
        self,
        domain: str = None,
        author_id: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出经验
        
        Args:
            domain: 领域过滤
            author_id: 作者过滤
            limit: 返回数量
            offset: 偏移量
        
        Returns:
            经验列表
        """
        require_config()
        
        conn = self._get_connection()
        
        sql = """
            SELECT id, code, title, summary, domain, tags, importance,
                   author_id, author_name, level, usage_count, helpful_count,
                   created_at, published_at
            FROM experiences
            WHERE status = 'published'
        """
        params = []
        
        if domain:
            sql += " AND domain = %s"
            params.append(domain)
        
        if author_id:
            sql += " AND author_id = %s"
            params.append(author_id)
        
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
        
        # 处理 tags
        for exp in results:
            if exp.get('tags') and isinstance(exp['tags'], str):
                try:
                    exp['tags'] = json.loads(exp['tags'])
                except:
                    exp['tags'] = []
        
        return results
    
    def update_experience(
        self,
        code: str,
        **kwargs
    ) -> bool:
        """
        更新经验
        
        Args:
            code: 经验代码
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        require_config()
        
        allowed_fields = {'title', 'summary', 'content', 'tags', 'importance', 'level', 'visibility', 'status'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        if 'tags' in updates and isinstance(updates['tags'], list):
            updates['tags'] = json.dumps(updates['tags'], ensure_ascii=False)
        
        updates['updated_at'] = int(time.time() * 1000)
        
        conn = self._get_connection()
        
        set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
        params = list(updates.values())
        params.append(code)
        
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE experiences SET {set_clause} WHERE code = %s",
                params
            )
            conn.commit()
        
        return cursor.rowcount > 0
    
    def delete_experience(self, code: str) -> bool:
        """
        删除经验（软删除，改为 archived 状态）
        """
        require_config()
        
        conn = self._get_connection()
        
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE experiences SET status = 'archived', updated_at = %s WHERE code = %s",
                (int(time.time() * 1000), code)
            )
            conn.commit()
        
        return cursor.rowcount > 0
    
    def __del__(self):
        """析构时关闭连接"""
        self._close()


class MemoryClient:
    """
    记忆客户端
    
    用于：
    - 存储本地记忆（不上传云端）
    - 搜索记忆
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self._connection: Optional[pymysql.Connection] = None
    
    def _get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        if not PYMYSQL_AVAILABLE:
            raise DatabaseError("PyMySQL 未安装")
        
        if self._connection is None or not self._connection.open:
            try:
                self._connection = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    charset=self.config.charset,
                    cursorclass=DictCursor,
                    connect_timeout=10,
                    read_timeout=30,
                    write_timeout=30,
                )
            except pymysql.Error as e:
                raise DatabaseError(f"数据库连接失败: {e}")
        
        return self._connection
    
    def _close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None
    
    def store_memory(
        self,
        content: str,
        memory_type: str = "general",
        visibility: str = "private",
        tags: List[str] = None,
        importance: float = 5.0,
        source_agent: str = "openclaw",
        source_agent_name: str = None,
        project_path: str = None,
        summary: str = None,
        md_content: str = None,
    ) -> Dict[str, Any]:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 类型 (general/project/preference/knowledge/team)
            visibility: 可见性 (private/shared/global)
            tags: 标签列表
            importance: 重要性
            source_agent: 来源Agent ID
            source_agent_name: 来源Agent显示名
            project_path: 关联项目路径
            summary: 摘要
            md_content: MD格式正文（可选）
        
        Returns:
            记忆元数据
        """
        require_config()
        
        if tags is None:
            tags = []
        
        # 生成唯一 ID
        memory_id = f"mem_{uuid.uuid4().hex[:10]}"
        
        # 时间戳
        now = int(time.time() * 1000)
        
        conn = self._get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO memories 
                   (id, content, summary, md_content, type, visibility, source,
                    source_agent, source_agent_name, project_path, importance, tags,
                    created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    memory_id, content, summary, md_content, memory_type, visibility,
                    "openclaw", source_agent, source_agent_name, project_path,
                    importance, json.dumps(tags, ensure_ascii=False),
                    now, now
                )
            )
            conn.commit()
        
        return {
            "id": memory_id,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "type": memory_type,
            "visibility": visibility,
            "tags": tags,
            "importance": importance,
            "created_at": now,
        }
    
    def search_memories(
        self,
        query: str = None,
        memory_type: str = None,
        visibility: str = None,
        source_agent: str = None,
        tags: List[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        """
        require_config()
        
        conn = self._get_connection()
        
        sql = """
            SELECT id, content, summary, type, visibility, source_agent,
                   source_agent_name, project_path, importance, tags, created_at
            FROM memories
            WHERE is_deleted = 0
        """
        params = []
        
        if query:
            sql += " AND (content LIKE %s OR summary LIKE %s)"
            like_query = f"%{query}%"
            params.extend([like_query, like_query])
        
        if memory_type:
            sql += " AND type = %s"
            params.append(memory_type)
        
        if visibility:
            sql += " AND visibility = %s"
            params.append(visibility)
        
        if source_agent:
            sql += " AND source_agent = %s"
            params.append(source_agent)
        
        if tags:
            for tag in tags:
                sql += " AND JSON_CONTAINS(tags, %s)"
                params.append(json.dumps(tag))
        
        sql += " ORDER BY importance DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
        
        # 处理 tags
        for mem in results:
            if mem.get('tags') and isinstance(mem['tags'], str):
                try:
                    mem['tags'] = json.loads(mem['tags'])
                except:
                    mem['tags'] = []
        
        return results
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记忆"""
        require_config()
        
        conn = self._get_connection()
        
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM memories WHERE id = %s AND is_deleted = 0",
                (memory_id,)
            )
            mem = cursor.fetchone()
        
        if mem and mem.get('tags') and isinstance(mem['tags'], str):
            try:
                mem['tags'] = json.loads(mem['tags'])
            except:
                mem['tags'] = []
        
        return mem
    
    def delete_memory(self, memory_id: str, hard: bool = False) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
            hard: 是否硬删除
        """
        require_config()
        
        conn = self._get_connection()
        
        with conn.cursor() as cursor:
            if hard:
                cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            else:
                cursor.execute(
                    "UPDATE memories SET is_deleted = 1, updated_at = %s WHERE id = %s",
                    (int(time.time() * 1000), memory_id)
                )
            conn.commit()
        
        return cursor.rowcount > 0
    
    def __del__(self):
        """析构时关闭连接"""
        self._close()


# 全局客户端实例
_experience_client: Optional[ExperienceClient] = None
_memory_client: Optional[MemoryClient] = None


def get_client(client_type: str = "experience") -> Any:
    """
    获取客户端实例
    
    Args:
        client_type: "experience" 或 "memory"
    """
    global _experience_client, _memory_client
    
    if client_type == "experience":
        if _experience_client is None:
            _experience_client = ExperienceClient()
        return _experience_client
    elif client_type == "memory":
        if _memory_client is None:
            _memory_client = MemoryClient()
        return _memory_client
    else:
        raise ValueError(f"Unknown client type: {client_type}")


# 便捷函数
def share_experience(**kwargs) -> Dict[str, Any]:
    """分享经验到云端"""
    return get_client("experience").share_experience(**kwargs)


def search_experiences(query: str, **kwargs) -> List[Dict[str, Any]]:
    """搜索云端经验"""
    return get_client("experience").search_experiences(query, **kwargs)


def get_experience(code: str) -> Optional[Dict[str, Any]]:
    """获取经验详情"""
    return get_client("experience").get_experience(code)


def list_experiences(**kwargs) -> List[Dict[str, Any]]:
    """列出经验"""
    return get_client("experience").list_experiences(**kwargs)


def store_memory(content: str, **kwargs) -> Dict[str, Any]:
    """存储记忆"""
    return get_client("memory").store_memory(content, **kwargs)


def search_memories(query: str = None, **kwargs) -> List[Dict[str, Any]]:
    """搜索记忆"""
    return get_client("memory").search_memories(query, **kwargs)
