# -*- coding: utf-8 -*-
"""
File Storage - 文件存储模块
用于存储和管理经验 MD 文件
"""

import os
import re
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


class FileStorage:
    """
    文件存储管理器
    
    支持本地文件存储和 HTTP 远程存储
    """
    
    def __init__(
        self,
        base_path: str = None,
        base_url: str = None,
        http_enabled: bool = False
    ):
        """
        Args:
            base_path: 本地存储基础路径
            base_url: HTTP 访问基础 URL
            http_enabled: 是否启用 HTTP 模式
        """
        self.base_path = Path(base_path) if base_path else Path.home() / ".memory" / "experiences"
        self.base_url = base_url or ""
        self.http_enabled = http_enabled
        
        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, code: str, title: str, tags: list) -> str:
        """
        生成文件名
        
        格式: {CODE}_{slugified_title}.md
        例如: EXP-BACKEND-FASTAPI-0001_FastAPI性能优化.md
        """
        # 清理标题为 slug
        slug = self._slugify(title)
        
        # 截取长度
        if len(slug) > 50:
            slug = slug[:50]
        
        return f"{code}_{slug}.md"
    
    def _slugify(self, text: str) -> str:
        """将文本转换为 slug"""
        # 移除特殊字符，只保留字母数字中文和连字符
        text = re.sub(r'[^\w\s\-]', '', text)
        # 替换空格为连字符
        text = re.sub(r'[\s]+', '-', text)
        # 转为小写
        return text.lower()
    
    def _get_date_path(self) -> str:
        """获取按日期组织的路径"""
        now = time.localtime()
        return f"{now.tm_year}-{now.tm_mon:02d}"
    
    def _compute_hash(self, content: str) -> str:
        """计算文件 SHA256 哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def save(
        self,
        code: str,
        title: str,
        content: str,
        tags: list = None,
        author_id: str = None
    ) -> Dict[str, Any]:
        """
        保存经验 MD 文件
        
        Args:
            code: 经验代码 (EXP-DOMAIN-TAG-SEQ)
            title: 经验标题
            content: MD 文件内容
            tags: 标签列表
            author_id: 作者 ID
        
        Returns:
            文件信息字典
        """
        # 生成文件名
        filename = self._generate_filename(code, title, tags or [])
        date_path = self._get_date_path()
        
        # 确保日期目录存在
        target_dir = self.base_path / date_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 完整文件路径
        file_path = target_dir / filename
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 计算哈希
        file_hash = self._compute_hash(content)
        file_size = os.path.getsize(file_path)
        
        # 相对路径（用于存储到数据库）
        relative_path = f"/{date_path}/{filename}"
        
        return {
            "code": code,
            "file_path": relative_path,
            "file_name": filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "full_path": str(file_path)
        }
    
    def load(self, file_path: str) -> Optional[str]:
        """
        加载经验 MD 文件内容
        
        Args:
            file_path: 文件路径（相对路径）
        
        Returns:
            文件内容或 None
        """
        # 处理路径
        if file_path.startswith('/'):
            file_path = file_path[1:]
        
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return None
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def delete(self, file_path: str) -> bool:
        """
        删除经验 MD 文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否成功
        """
        if file_path.startswith('/'):
            file_path = file_path[1:]
        
        full_path = self.base_path / file_path
        
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        if file_path.startswith('/'):
            file_path = file_path[1:]
        
        full_path = self.base_path / file_path
        return full_path.exists()
    
    def get_url(self, file_path: str) -> str:
        """获取文件的 HTTP URL"""
        if self.http_enabled and self.base_url:
            if file_path.startswith('/'):
                file_path = file_path[1:]
            return f"{self.base_url}/{file_path}"
        return str(self.base_path / file_path)
    
    def list_files(self, date_path: str = None) -> list:
        """
        列出文件
        
        Args:
            date_path: 日期路径，如 "2026-04"
        
        Returns:
            文件列表
        """
        if date_path:
            target_dir = self.base_path / date_path
        else:
            target_dir = self.base_path
        
        if not target_dir.exists():
            return []
        
        files = []
        for f in target_dir.rglob("*.md"):
            relative = f.relative_to(self.base_path)
            files.append({
                "path": "/" + str(relative),
                "name": f.name,
                "size": os.path.getsize(f)
            })
        
        return files


# 全局实例
_file_storage: Optional[FileStorage] = None


def get_file_storage(
    base_path: str = None,
    base_url: str = None,
    http_enabled: bool = False
) -> FileStorage:
    """获取全局文件存储实例"""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorage(
            base_path=base_path,
            base_url=base_url,
            http_enabled=http_enabled
        )
    return _file_storage
