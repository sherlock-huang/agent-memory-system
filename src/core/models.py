# -*- coding: utf-8 -*-
"""
Memory System Data Models
数据模型定义
"""

import uuid
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型枚举"""
    GENERAL = "general"
    PROJECT = "project"
    PREFERENCE = "preference"
    KNOWLEDGE = "knowledge"
    TEAM = "team"


class Visibility(str, Enum):
    """可见性枚举"""
    PRIVATE = "private"      # 仅创建者可见
    SHARED = "shared"       # 同项目/团队可见
    GLOBAL = "global"       # 所有 Agent 可见


class Source(str, Enum):
    """来源枚举"""
    CLI = "cli"
    OPENCLAW = "openclaw"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    KIMI = "kimi_code"
    CURSOR = "cursor"


@dataclass
class Memory:
    """
    记忆数据模型
    
    Attributes:
        id: 唯一标识，格式: mem_xxxxxxxxxx
        content: 记忆内容
        summary: 摘要 (可选)
        type: 记忆类型 (general/project/preference/knowledge/team)
        visibility: 可见性 (private/shared/global)
        source: 来源 Agent 类型
        source_agent: 来源 Agent ID
        project_path: 关联项目路径
        importance: 重要性 1-10
        tags: 标签列表
        created_at: 创建时间戳 (ms)
        updated_at: 更新时间戳 (ms)
        is_deleted: 是否已删除
        
        # 经验分享专用字段（当 share_title 不为空时为经验）
        share_title: Optional[str] = None  # 经验名称（唯一标题）
        md_content: Optional[str] = None  # MD格式正文
        notes: Optional[str] = None       # 备注
    """
    
    content: str
    type: str = MemoryType.GENERAL.value
    visibility: str = Visibility.PRIVATE.value  # 默认改为 private
    source: str = Source.CLI.value
    source_agent: Optional[str] = None
    project_path: Optional[str] = None
    summary: Optional[str] = None
    importance: float = 5.0
    tags: List[str] = field(default_factory=list)
    
    id: str = field(default_factory=lambda: "")
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    is_deleted: bool = False
    
    # 经验分享专用字段
    share_title: Optional[str] = None  # 经验名称（如不为空，表示这是一条经验）
    md_content: Optional[str] = None    # MD格式正文
    notes: Optional[str] = None         # 备注
    
    def __post_init__(self):
        if not self.id:
            self.id = f"mem_{uuid.uuid4().hex[:10]}"
        
        if isinstance(self.tags, str):
            try:
                self.tags = json.loads(self.tags)
            except:
                self.tags = []
    
    def is_experience(self) -> bool:
        """是否是经验（有无经验名称）"""
        return bool(self.share_title)
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式（经验专用）"""
        if not self.share_title:
            return self.content
        
        lines = [
            f"# {self.share_title}",
            "",
        ]
        
        if self.summary:
            lines.append("## 摘要")
            lines.append(self.summary)
            lines.append("")
        
        if self.tags:
            lines.append("## 标签")
            lines.append(" " + " ".join(f"#{t}" for t in self.tags))
            lines.append("")
        
        if self.md_content:
            lines.append("## 正文")
            lines.append(self.md_content)
            lines.append("")
        elif self.content:
            lines.append("## 正文")
            lines.append(self.content)
            lines.append("")
        
        if self.notes:
            lines.append("## 备注")
            lines.append(self.notes)
            lines.append("")
        
        lines.append(f"---")
        lines.append(f"*来源: {self.source_agent or 'unknown'} | 重要性: {self.importance}/10*")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = asdict(self)
        # 确保 tags 是列表
        if isinstance(d.get('tags'), str):
            try:
                d['tags'] = json.loads(d['tags'])
            except:
                d['tags'] = []
        # 转换所有非标准类型为标准 Python 类型
        for k, v in d.items():
            # 跳过 None, str, list, dict, bool
            if v is None or isinstance(v, (str, list, dict, bool)):
                continue
            # 转换数值类型
            if isinstance(v, (int, float)):
                # 确保 float 类型的精度
                if isinstance(v, float):
                    try:
                        d[k] = float(v)
                    except:
                        pass
            # 转换 Decimal
            try:
                from decimal import Decimal
                if isinstance(v, Decimal):
                    d[k] = float(v)
            except ImportError:
                pass
            # 转换 bytes
            if isinstance(v, bytes):
                d[k] = str(v)
        return d
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        # 处理 tags
        if 'tags' in d and isinstance(d['tags'], str):
            try:
                d['tags'] = json.loads(d['tags'])
            except:
                d['tags'] = []
        
        # 过滤掉非字段的键
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        
        return cls(**filtered)
    
    def update_content(self, content: str, **kwargs):
        """更新内容"""
        self.content = content
        self.updated_at = int(time.time() * 1000)
        
        if 'summary' in kwargs:
            self.summary = kwargs['summary']
        if 'importance' in kwargs:
            self.importance = kwargs['importance']
        if 'tags' in kwargs:
            self.tags = kwargs['tags']
        if 'visibility' in kwargs:
            self.visibility = kwargs['visibility']
    
    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.updated_at = int(time.time() * 1000)
    
    def __repr__(self) -> str:
        return f"<Memory {self.id}: {self.content[:50]}...>"


@dataclass
class SearchResult:
    """
    搜索结果模型
    
    Attributes:
        memory: 记忆对象
        score: 相关性分数
        highlight: 高亮片段 (可选)
    """
    memory: Memory
    score: float = 0.0
    highlight: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 获取 memory 的字典
        memory_dict = self.memory.to_dict() if hasattr(self.memory, 'to_dict') else dict(self.memory)
        
        # 确保所有数值类型可序列化
        for k, v in memory_dict.items():
            if v is None or isinstance(v, (str, list, bool)):
                continue
            if isinstance(v, (int, float)):
                try:
                    # 尝试转换为 Python 原生类型
                    float(v)
                except:
                    memory_dict[k] = str(v)
            else:
                # 其他类型转为字符串
                memory_dict[k] = str(v)
        
        # 确保 score 是普通 Python float
        score_val = self.score
        try:
            score_val = float(score_val)
        except:
            score_val = 0.0
        
        result = dict(memory_dict)
        result['score'] = score_val
        result['highlight'] = self.highlight
        return result


@dataclass 
class Agent:
    """
    Agent 注册模型
    
    Attributes:
        id: Agent 唯一 ID
        type: Agent 类型 (openclaw/claude_code/codex/kimi/cursor)
        name: 显示名称
        api_key_hash: API Key hash
        registered_at: 注册时间
        last_seen: 最后活跃时间
    """
    
    id: str
    type: str
    name: Optional[str] = None
    api_key_hash: Optional[str] = None
    registered_at: int = field(default_factory=lambda: int(time.time() * 1000))
    last_seen: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Agent":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class ACL:
    """
    访问控制模型
    
    Attributes:
        memory_id: 记忆 ID
        agent_id: Agent ID
        permission: 权限 (read/write/admin)
        granted_by: 授权者
        granted_at: 授权时间
        expires_at: 过期时间 (可选)
    """
    
    memory_id: str
    agent_id: str
    permission: str
    granted_by: str
    granted_at: int = field(default_factory=lambda: int(time.time() * 1000))
    expires_at: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
