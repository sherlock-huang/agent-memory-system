# -*- coding: utf-8 -*-
"""
Memory Store Engine
存储引擎模块
"""

import json
import uuid
import time
from typing import Optional, List, Dict, Any

from .database import get_db
from .models import Memory, MemoryType, Visibility, Source
from .config import get_config


class StoreEngine:
    """
    记忆存储引擎
    
    负责:
    - 创建新记忆
    - 更新记忆
    - 删除记忆
    - 生成摘要
    """
    
    def __init__(self):
        self.db = get_db()
        self.config = get_config()
    
    def store(
        self,
        content: str,
        memory_type: str = MemoryType.GENERAL.value,
        visibility: str = Visibility.PRIVATE.value,  # 默认为 private
        tags: List[str] = None,
        importance: float = 5.0,
        project_path: str = None,
        source_agent: str = None,
        summary: str = None,
        auto_summary: bool = True,
        # 经验分享专用字段
        share_title: str = None,
        md_content: str = None,
        notes: str = None,
    ) -> Memory:
        """
        存储新记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型 (general/project/preference/knowledge/team)
            visibility: 可见性 (private/shared/global)
            tags: 标签列表
            importance: 重要性 1-10
            project_path: 关联项目路径
            source_agent: 来源 Agent ID
            summary: 摘要 (可选)
            auto_summary: 是否自动生成摘要
            share_title: 经验名称（如果设置，表示这是一条经验）
            md_content: MD格式正文（经验专用）
            notes: 备注（经验专用）
        
        Returns:
            Memory 对象
        """
        # 验证参数
        if not content or not content.strip():
            raise ValueError("content cannot be empty")
        
        if importance < 1 or importance > 10:
            raise ValueError("importance must be between 1 and 10")
        
        # 自动生成摘要
        if not summary and auto_summary and len(content) > 200:
            summary = self._generate_summary(content)
        
        # 获取来源
        source = self.config.source
        if not source_agent:
            source_agent = self.config.agent_id
        
        # 创建记忆
        memory = Memory(
            content=content.strip(),
            summary=summary,
            type=memory_type,
            visibility=visibility,
            source=source,
            source_agent=source_agent,
            project_path=project_path,
            importance=importance,
            tags=tags or [],
            # 经验分享专用字段
            share_title=share_title,
            md_content=md_content or content,  # 默认用 content
            notes=notes,
        )
        
        # 插入数据库
        self.db.insert_memory(memory)
        
        return memory
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        memory_type: str = None,
        visibility: str = None,
        tags: List[str] = None,
        importance: float = None,
        summary: str = None,
        # 经验分享专用字段
        share_title: str = None,
        md_content: str = None,
        notes: str = None,
    ) -> Optional[Memory]:
        """
        更新记忆
        
        Args:
            memory_id: 记忆 ID
            content: 新内容
            memory_type: 新类型
            visibility: 新可见性
            tags: 新标签
            importance: 新重要性
            summary: 新摘要
            share_title: 经验名称
            md_content: MD格式正文
            notes: 备注
        
        Returns:
            更新后的 Memory 或 None
        """
        memory = self.db.get_memory(memory_id)
        if not memory:
            return None
        
        # 更新字段
        if content is not None:
            memory.content = content.strip()
        
        if summary is not None:
            memory.summary = summary
        elif content and len(content) > 200 and not memory.summary:
            memory.summary = self._generate_summary(content)
        
        if memory_type is not None:
            memory.type = memory_type
        
        if visibility is not None:
            memory.visibility = visibility
        
        if tags is not None:
            memory.tags = tags
        
        if importance is not None:
            if importance < 1 or importance > 10:
                raise ValueError("importance must be between 1 and 10")
            memory.importance = importance
        
        # 经验分享专用字段更新
        if share_title is not None:
            memory.share_title = share_title
        if md_content is not None:
            memory.md_content = md_content
        if notes is not None:
            memory.notes = notes
        
        memory.updated_at = int(time.time() * 1000)
        
        # 保存
        self.db.update_memory(memory)
        
        return memory
    
    def delete(self, memory_id: str, hard: bool = False) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            hard: 是否永久删除
        
        Returns:
            是否成功
        """
        if hard:
            return self.db.delete_memory(memory_id, hard=True)
        else:
            memory = self.db.get_memory(memory_id)
            if not memory:
                return False
            
            memory.soft_delete()
            return self.db.update_memory(memory)
    
    def restore(self, memory_id: str) -> bool:
        """
        恢复已删除的记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            是否成功
        """
        return self.db.restore_memory(memory_id)
    
    def get(self, memory_id: str) -> Optional[Memory]:
        """
        获取记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            Memory 或 None
        """
        return self.db.get_memory(memory_id)
    
    def list(
        self,
        memory_type: str = None,
        project_path: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        """
        列出记忆
        
        Args:
            memory_type: 类型过滤
            project_path: 项目路径过滤
            limit: 返回数量
            offset: 跳过数量
        
        Returns:
            Memory 列表
        """
        return self.db.list_memories(
            memory_type=memory_type,
            project_path=project_path,
            limit=limit,
            offset=offset
        )
    
    def count(
        self,
        memory_type: str = None,
        project_path: str = None
    ) -> int:
        """
        统计记忆数量
        
        Args:
            memory_type: 类型过滤
            project_path: 项目路径过滤
        
        Returns:
            数量
        """
        return self.db.count_memories(
            memory_type=memory_type,
            project_path=project_path
        )
    
    def stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        return self.db.get_stats()
    
    def _generate_summary(self, content: str, max_length: int = 150) -> str:
        """
        生成摘要
        
        简单实现: 取前 N 个字符
        生产环境可以调用 LLM API
        
        Args:
            content: 内容
            max_length: 最大长度
        
        Returns:
            摘要
        """
        if len(content) <= max_length:
            return content
        
        # 在单词边界截断
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + "..."


# 全局实例
_store: Optional[StoreEngine] = None


def get_store() -> StoreEngine:
    """获取全局存储引擎"""
    global _store
    if _store is None:
        _store = StoreEngine()
    return _store
