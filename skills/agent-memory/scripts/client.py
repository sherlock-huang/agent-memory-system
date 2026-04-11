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


class ReviewClient:
    """
    审核客户端

    用于：
    - 请求审核（发起 review）
    - 提交审核决定（批准/驳回/要求修改）
    - 添加批注
    - 查询审核状态
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
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _log_activity(
        self,
        conn,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        target_title: str = None,
        detail: dict = None,
    ):
        """记录活动日志"""
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO activity_log
                   (id, actor_id, action, target_type, target_id, target_title, detail, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    self._generate_id("log"),
                    actor_id,
                    action,
                    target_type,
                    target_id,
                    target_title,
                    json.dumps(detail or {}, ensure_ascii=False),
                    self._now_ms(),
                ),
            )

    def request_review(
        self,
        experience_code: str,
        requester_id: str,
        requester_name: str = None,
        reviewer_id: str = None,
        comment: str = None,
        agent_id: str = "openclaw",
    ) -> Dict[str, Any]:
        """
        请求审核（提交经验供审核）

        Args:
            experience_code: 经验代码
            requester_id: 请求者Agent ID（作者）
            requester_name: 请求者显示名
            reviewer_id: 指定审核人ID（可选，默认由系统分配）
            comment: 附言
            agent_id: 当前操作用的Agent标识

        Returns:
            包含 review_id 和经验状态的字典
        """
        require_config()
        conn = self._get_connection()
        now = self._now_ms()
        review_id = self._generate_id("rev")

        with conn.cursor() as cursor:
            # 获取经验信息
            cursor.execute(
                "SELECT id, title, author_id, status FROM experiences WHERE code = %s",
                (experience_code,),
            )
            exp = cursor.fetchone()
            if not exp:
                raise DatabaseError(f"经验不存在: {experience_code}")

            if exp["author_id"] == requester_id and reviewer_id is None:
                raise DatabaseError("不能审核自己的经验（reviewer_id 不能与 author_id 相同）")

            # 更新经验状态
            cursor.execute(
                """UPDATE experiences
                   SET status = 'pending_review',
                       reviewer_id = COALESCE(%s, reviewer_id),
                       review_requested_at = %s
                   WHERE code = %s""",
                (reviewer_id, now, experience_code),
            )

            # 创建 review 记录
            cursor.execute(
                """INSERT INTO reviews
                   (id, experience_code, experience_id, reviewer_id, reviewer_name,
                    status, requester_id, comment, version_at_review, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, 'requested', %s, %s, %s, %s, %s)""",
                (
                    review_id,
                    experience_code,
                    exp["id"],
                    reviewer_id or "system",
                    requester_name,
                    requester_id,
                    comment,
                    1,
                    now,
                    now,
                ),
            )

            # 活动日志
            self._log_activity(
                conn,
                actor_id=requester_id,
                action="review_requested",
                target_type="experience",
                target_id=experience_code,
                target_title=exp["title"],
                detail={"reviewer_id": reviewer_id, "comment": comment},
            )

            conn.commit()

        return {
            "review_id": review_id,
            "experience_code": experience_code,
            "status": "pending_review",
            "reviewer_id": reviewer_id,
            "created_at": now,
        }

    def submit_review(
        self,
        review_id: str,
        reviewer_id: str,
        decision: str,  # "approve" | "request_changes" | "reject"
        comment: str = None,
        agent_id: str = "openclaw",
    ) -> Dict[str, Any]:
        """
        提交审核决定

        Args:
            review_id: Review ID
            reviewer_id: 审核人ID
            decision: 决定（approve / request_changes / reject）
            comment: 审核意见

        Returns:
            包含审核结果的字典
        """
        require_config()
        if decision not in ("approve", "request_changes", "reject"):
            raise ValueError("decision 必须是 approve / request_changes / reject")

        conn = self._get_connection()
        now = self._now_ms()

        with conn.cursor() as cursor:
            # 获取 review 信息
            cursor.execute(
                "SELECT * FROM reviews WHERE id = %s AND status = 'requested' FOR UPDATE",
                (review_id,),
            )
            review = cursor.fetchone()
            if not review:
                raise DatabaseError(f"Review 不存在或已完成: {review_id}")

            # 权限检查：只有被指定的 reviewer 才能审核
            if review["reviewer_id"] not in (reviewer_id, "system"):
                raise DatabaseError(f"你不是该经验的指定审核人")

            # 更新 review 记录
            new_status = "approved" if decision == "approve" else "changes_requested"
            cursor.execute(
                """UPDATE reviews
                   SET status = %s, decision = %s, comment = COALESCE(%s, comment),
                       updated_at = %s, resolved_at = %s
                   WHERE id = %s""",
                (new_status, decision, comment, now, now, review_id),
            )

            # 更新经验状态
            if decision == "approve":
                exp_status = "published"
            elif decision == "request_changes":
                exp_status = "revision_requested"
            else:
                exp_status = "archived"

            cursor.execute(
                """UPDATE experiences
                   SET status = %s, approved_by = %s, reviewed_at = %s,
                       rejection_reason = %s
                   WHERE code = %s""",
                (
                    exp_status,
                    reviewer_id if decision == "approve" else None,
                    now if decision != "approve" else None,
                    comment if decision in ("request_changes", "reject") else None,
                    review["experience_code"],
                ),
            )

            # 活动日志
            action_map = {
                "approve": "review_approved",
                "request_changes": "review_changes_requested",
                "reject": "review_changes_requested",
            }
            cursor.execute(
                "SELECT title FROM experiences WHERE code = %s",
                (review["experience_code"],),
            )
            exp = cursor.fetchone()
            self._log_activity(
                conn,
                actor_id=reviewer_id,
                action=action_map[decision],
                target_type="experience",
                target_id=review["experience_code"],
                target_title=exp["title"] if exp else None,
                detail={"decision": decision, "comment": comment},
            )

            conn.commit()

        return {
            "review_id": review_id,
            "decision": decision,
            "status": new_status,
            "experience_status": exp_status,
            "resolved_at": now,
        }

    def add_comment(
        self,
        review_id: str,
        author_id: str,
        comment: str,
        author_name: str = None,
        line_number: int = None,
        field_name: str = None,
        severity: str = "suggestion",
        agent_id: str = "openclaw",
    ) -> Dict[str, Any]:
        """
        添加审核批注

        Args:
            review_id: Review ID
            author_id: 批注作者ID
            author_name: 批注作者显示名
            comment: 批注内容
            line_number: 行号（可选）
            field_name: 字段名（可选）
            severity: 严重程度 (suggestion/warning/error)

        Returns:
            批注记录
        """
        require_config()
        conn = self._get_connection()
        now = self._now_ms()
        comment_id = self._generate_id("rcm")

        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO review_comments
                   (id, review_id, line_number, field_name, comment, severity,
                    author_id, author_name, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    comment_id,
                    review_id,
                    line_number,
                    field_name,
                    comment,
                    severity,
                    author_id,
                    author_name,
                    now,
                ),
            )

            # 更新 review 更新时间
            cursor.execute(
                "UPDATE reviews SET updated_at = %s WHERE id = %s",
                (now, review_id),
            )

            # 活动日志
            cursor.execute(
                "SELECT experience_code FROM reviews WHERE id = %s",
                (review_id,),
            )
            rev = cursor.fetchone()
            self._log_activity(
                conn,
                actor_id=author_id,
                action="review_commented",
                target_type="review",
                target_id=review_id,
                target_title=f"批注 on {rev['experience_code']}" if rev else review_id,
                detail={"line": line_number, "field": field_name, "severity": severity},
            )

            conn.commit()

        return {
            "id": comment_id,
            "review_id": review_id,
            "line_number": line_number,
            "field_name": field_name,
            "comment": comment,
            "severity": severity,
            "resolved": False,
            "created_at": now,
        }

    def resolve_comment(
        self,
        comment_id: str,
        resolved_by: str,
        agent_id: str = "openclaw",
    ) -> Dict[str, Any]:
        """标记批注为已解决"""
        require_config()
        conn = self._get_connection()
        now = self._now_ms()

        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE review_comments
                   SET resolved = 1, resolved_by = %s, resolved_at = %s
                   WHERE id = %s""",
                (resolved_by, now, comment_id),
            )
            cursor.execute("SELECT review_id FROM review_comments WHERE id = %s", (comment_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE reviews SET updated_at = %s WHERE id = %s", (now, row["review_id"]))
            conn.commit()

        return {"comment_id": comment_id, "resolved": True, "resolved_at": now}

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """获取 Review 详情（含批注列表）"""
        require_config()
        conn = self._get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
            review = cursor.fetchone()

        if not review:
            return None

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM review_comments WHERE review_id = %s ORDER BY created_at",
                (review_id,),
            )
            comments = cursor.fetchall()

        review["comments"] = comments
        return review

    def list_reviews(
        self,
        experience_code: str = None,
        reviewer_id: str = None,
        status: str = None,
        requester_id: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出 Review"""
        require_config()
        conn = self._get_connection()

        sql = "SELECT * FROM reviews WHERE 1=1"
        params = []

        if experience_code:
            sql += " AND experience_code = %s"
            params.append(experience_code)
        if reviewer_id:
            sql += " AND reviewer_id = %s"
            params.append(reviewer_id)
        if status:
            sql += " AND status = %s"
            params.append(status)
        if requester_id:
            sql += " AND requester_id = %s"
            params.append(requester_id)

        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def list_pending_for_reviewer(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """列出待我审核的经验（via 视图）"""
        require_config()
        conn = self._get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT v.*, r.id AS review_id, r.status AS review_status,
                          r.comment AS review_comment, r.created_at AS review_created_at
                   FROM v_pending_reviews v
                   JOIN reviews r ON v.code = r.experience_code AND r.status = 'requested'
                   WHERE r.reviewer_id = %s
                   ORDER BY r.created_at ASC""",
                (reviewer_id,),
            )
            return cursor.fetchall()

    def get_experience_with_reviews(self, code: str) -> Optional[Dict[str, Any]]:
        """获取经验详情 + 所有相关 Review"""
        exp = get_client("experience").get_experience(code)
        if not exp:
            return None
        reviews = self.list_reviews(experience_code=code)
        exp["reviews"] = reviews
        return exp

    def __del__(self):
        self._close()


# 全局客户端实例
_review_client: Optional[ReviewClient] = None


def get_review_client() -> ReviewClient:
    global _review_client
    if _review_client is None:
        _review_client = ReviewClient()
    return _review_client


# 便捷函数
def request_review(experience_code: str, requester_id: str, **kwargs) -> Dict[str, Any]:
    return get_review_client().request_review(experience_code, requester_id, **kwargs)


def submit_review(review_id: str, reviewer_id: str, decision: str, **kwargs) -> Dict[str, Any]:
    return get_review_client().submit_review(review_id, reviewer_id, decision, **kwargs)


def add_review_comment(review_id: str, author_id: str, comment: str, author_name: str = None, **kwargs) -> Dict[str, Any]:
    return get_review_client().add_comment(review_id, author_id, comment, **kwargs)


def resolve_review_comment(comment_id: str, resolved_by: str, **kwargs) -> Dict[str, Any]:
    return get_review_client().resolve_comment(comment_id, resolved_by, **kwargs)


def get_review(review_id: str) -> Optional[Dict[str, Any]]:
    return get_review_client().get_review(review_id)


def list_reviews(**kwargs) -> List[Dict[str, Any]]:
    return get_review_client().list_reviews(**kwargs)


def list_pending_reviews(reviewer_id: str) -> List[Dict[str, Any]]:
    return get_review_client().list_pending_for_reviewer(reviewer_id)


def get_experience_full(code: str) -> Optional[Dict[str, Any]]:
    return get_review_client().get_experience_with_reviews(code)


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
        client_type: "experience" / "memory" / "review"
    """
    global _experience_client, _memory_client, _review_client
    
    if client_type == "experience":
        if _experience_client is None:
            _experience_client = ExperienceClient()
        return _experience_client
    elif client_type == "memory":
        if _memory_client is None:
            _memory_client = MemoryClient()
        return _memory_client
    elif client_type == "review":
        if _review_client is None:
            _review_client = ReviewClient()
        return _review_client
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
