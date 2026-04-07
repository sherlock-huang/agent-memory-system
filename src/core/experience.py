# -*- coding: utf-8 -*-
"""
Experience Model - 经验数据模型
"""

import uuid
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class ExperienceType(str, Enum):
    """经验类型"""
    TECHNICAL = "technical"
    PRODUCT = "product"
    OPERATION = "operation"
    MANAGEMENT = "management"


class ExperienceLevel(str, Enum):
    """难度级别"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ExperienceStatus(str, Enum):
    """状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExperienceVisibility(str, Enum):
    """可见性"""
    PRIVATE = "private"
    SHARED = "shared"
    GLOBAL = "global"


class Domain(str, Enum):
    """领域"""
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    DEVOPS = "DEVOPS"
    AI = "AI"
    SECURITY = "SECURITY"
    DATABASE = "DATABASE"
    GENERAL = "GENERAL"


@dataclass
class Experience:
    """
    经验数据模型
    
    Attributes:
        id: 内部唯一标识 (mem_xxxxxxxxxx)
        code: 可读唯一标识 (EXP-DOMAIN-TAG-SEQ)
        title: 经验标题
        summary: 一句话摘要
        tags: 标签列表
        importance: 重要性 1-10
        
        file_path: MD 文件路径
        file_hash: SHA256 校验
        
        author_id: 作者 Agent ID
        author_name: 作者显示名
        author_type: 来源类型
        
        type: 经验类型
        domain: 领域
        level: 难度级别
        
        quality_score: 质量评分 0-10
        usage_count: 查阅次数
        helpful_count: 点赞数
        
        related_codes: 相关经验代码列表
        version: 版本号
        language_code: 语言代码
        
        status: 状态
        visibility: 可见性
        
        contributors: 贡献者列表
        approved_by: 审批人
        
        created_at: 创建时间戳 (ms)
        updated_at: 更新时间戳 (ms)
        published_at: 发布时间戳 (ms)
    """
    
    # 核心内容
    title: str
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 5.0
    
    # 唯一标识
    id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:10]}")
    code: str = ""
    
    # 文件
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    
    # 作者
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_type: str = "openclaw"
    
    # 分类
    type: str = ExperienceType.TECHNICAL.value
    domain: str = Domain.GENERAL.value
    level: str = ExperienceLevel.INTERMEDIATE.value
    
    # 质量
    quality_score: float = 5.0
    usage_count: int = 0
    helpful_count: int = 0
    
    # 关联
    related_codes: List[str] = field(default_factory=list)
    version: int = 1
    language_code: str = "zh"
    
    # 状态
    status: str = ExperienceStatus.PUBLISHED.value
    visibility: str = ExperienceVisibility.SHARED.value
    
    # 协作
    contributors: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    
    # 时间
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    published_at: Optional[int] = None
    
    def __post_init__(self):
        # 确保 tags 是列表
        if isinstance(self.tags, str):
            try:
                self.tags = json.loads(self.tags)
            except:
                self.tags = []
        
        # 确保 related_codes 是列表
        if isinstance(self.related_codes, str):
            try:
                self.related_codes = json.loads(self.related_codes)
            except:
                self.related_codes = []
        
        # 确保 contributors 是列表
        if isinstance(self.contributors, str):
            try:
                self.contributors = json.loads(self.contributors)
            except:
                self.contributors = []
    
    @classmethod
    def generate_code(cls, domain: str, primary_tag: str, seq: int) -> str:
        """
        生成经验代码
        
        格式: {DOMAIN}-{TAG}-{SEQ:4}
        例如: EXP-BACKEND-FASTAPI-0001
        
        Args:
            domain: 领域 (BACKEND/FRONTEND/AI 等)
            primary_tag: 主要标签 (FASTAPI/DOCKER 等)
            seq: 序号
        
        Returns:
            经验代码
        """
        domain = domain.upper()[:10]
        tag = primary_tag.upper()[:10]
        return f"EXP-{domain}-{tag}-{seq:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = asdict(self)
        
        # 确保 tags 等是列表
        for key in ['tags', 'related_codes', 'contributors']:
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except:
                    d[key] = []
        
        # 转换数值类型
        for k, v in d.items():
            if v is None:
                continue
            try:
                from decimal import Decimal
                if isinstance(v, Decimal):
                    d[k] = float(v)
            except ImportError:
                pass
        
        return d
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            f"# {self.title}",
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
        
        if self.code:
            lines.append(f"**代码**: `{self.code}`")
            lines.append("")
        
        lines.append(f"*来源: {self.author_name or self.author_id or 'unknown'} | ")
        lines.append(f"领域: {self.domain} | ")
        lines.append(f"重要性: {self.importance}/10*")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Experience":
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
    
    def __repr__(self) -> str:
        return f"<Experience {self.code}: {self.title[:30]}...>"
