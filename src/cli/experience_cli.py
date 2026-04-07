# -*- coding: utf-8 -*-
"""
Experience CLI - 经验管理命令
"""

import json
import re
from typing import Optional, List, Dict, Any

from ..core.experience import (
    Experience, ExperienceType, ExperienceLevel,
    ExperienceStatus, ExperienceVisibility, Domain
)


class ExperienceCLI:
    """经验管理 CLI"""
    
    # Domain 到默认标签的映射
    DOMAIN_TAGS = {
        "BACKEND": "backend",
        "FRONTEND": "frontend", 
        "DEVOPS": "devops",
        "AI": "ai",
        "SECURITY": "security",
        "DATABASE": "database",
        "GENERAL": "general",
    }
    
    def __init__(self, db=None, file_storage=None):
        self.db = db
        self.file_storage = file_storage
    
    def _parse_domain(self, domain_str: str) -> str:
        """解析 domain 字符串"""
        domain_str = domain_str.upper()
        if domain_str in [d.value for d in Domain]:
            return domain_str
        # 尝试匹配
        for d in Domain:
            if d.value.startswith(domain_str):
                return d.value
        return Domain.GENERAL.value
    
    def _parse_level(self, level_str: str) -> str:
        """解析 level 字符串"""
        level_str = level_str.lower()
        if level_str in [l.value for l in ExperienceLevel]:
            return level_str
        if level_str in ["beginner", "beginner", "low", "easy"]:
            return ExperienceLevel.BEGINNER.value
        if level_str in ["advanced", "high", "hard"]:
            return ExperienceLevel.ADVANCED.value
        return ExperienceLevel.INTERMEDIATE.value
    
    def _extract_primary_tag(self, tags: List[str], domain: str) -> str:
        """提取主要标签"""
        if tags:
            # 使用第一个标签
            return tags[0].upper()[:10]
        # 使用 domain 的默认标签
        return self.DOMAIN_TAGS.get(domain, "GENERAL")[:10]
    
    def _get_next_seq(self, domain: str, primary_tag: str) -> int:
        """获取下一个序号"""
        # 这里需要查询数据库获取当前最大序号
        # 暂时使用随机数，生产环境需要从数据库查询
        import random
        return random.randint(1, 9999)
    
    def _validate_code_format(self, code: str) -> bool:
        """验证代码格式"""
        pattern = r'^EXP-[A-Z]{1,10}-[A-Z]{1,10}-\d{4}$'
        return bool(re.match(pattern, code))
    
    def _build_code(self, domain: str, tags: List[str], seq: int = None) -> str:
        """
        构建经验代码
        
        格式: EXP-{DOMAIN}-{TAG}-{SEQ:4}
        例如: EXP-BACKEND-FASTAPI-0001
        """
        domain = domain.upper()[:10]
        primary_tag = self._extract_primary_tag(tags, domain)
        
        if seq is None:
            seq = self._get_next_seq(domain, primary_tag)
        
        return f"EXP-{domain}-{primary_tag}-{seq:04d}"
    
    def create_experience(
        self,
        title: str,
        content: str,
        summary: str = "",
        tags: List[str] = None,
        domain: str = "GENERAL",
        level: str = "intermediate",
        importance: float = 7.0,
        author_id: str = None,
        author_name: str = None,
        author_type: str = "openclaw",
        related_codes: List[str] = None,
        visibility: str = "shared",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建经验
        
        Args:
            title: 经验标题
            content: MD 内容
            summary: 摘要
            tags: 标签列表
            domain: 领域
            level: 难度
            importance: 重要性
            author_id: 作者 ID
            author_name: 作者名
            author_type: 作者类型
            related_codes: 相关代码
            visibility: 可见性
        
        Returns:
            经验信息
        """
        tags = tags or []
        domain = self._parse_domain(domain)
        level = self._parse_level(level)
        
        # 生成代码
        code = self._build_code(domain, tags)
        
        # 保存文件
        file_info = None
        if self.file_storage and content:
            file_info = self.file_storage.save(
                code=code,
                title=title,
                content=content,
                tags=tags,
                author_id=author_id
            )
        
        # 创建经验对象
        exp = Experience(
            title=title,
            summary=summary,
            tags=tags,
            importance=importance,
            code=code,
            domain=domain,
            level=level,
            author_id=author_id,
            author_name=author_name,
            author_type=author_type,
            related_codes=related_codes or [],
            visibility=visibility,
            file_path=file_info["file_path"] if file_info else None,
            file_hash=file_info["file_hash"] if file_info else None,
        )
        
        return {
            "status": "created",
            "experience": exp.to_dict(),
            "file": file_info
        }
    
    def get_experience(self, code: str) -> Optional[Experience]:
        """获取经验"""
        # 需要从数据库查询
        pass
    
    def search_experiences(
        self,
        query: str = None,
        domain: str = None,
        tags: List[str] = None,
        level: str = None,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """搜索经验"""
        # 需要从数据库查询
        pass
    
    def list_experiences(
        self,
        domain: str = None,
        author_id: str = None,
        limit: int = 50,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """列出经验"""
        pass


# 全局实例
_exp_cli: Optional[ExperienceCLI] = None


def get_exp_cli() -> ExperienceCLI:
    """获取全局 ExperienceCLI 实例"""
    global _exp_cli
    if _exp_cli is None:
        _exp_cli = ExperienceCLI()
    return _exp_cli
