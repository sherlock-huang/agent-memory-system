# -*- coding: utf-8 -*-
"""
Memory Search Engine
搜索引擎模块
"""

from typing import List, Optional, Dict, Any, Tuple

from .database import get_db
from .models import Memory, SearchResult
from .config import get_config


class SearchEngine:
    """
    记忆搜索引擎
    
    支持:
    - 关键词搜索
    - 类型过滤
    - 项目过滤
    - 相关性排序
    """
    
    def __init__(self):
        self.db = get_db()
        self.config = get_config()
    
    def search(
        self,
        query: str,
        memory_type: str = None,
        project_path: str = None,
        visibility: str = None,
        limit: int = None,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        搜索记忆
        
        Args:
            query: 搜索内容
            memory_type: 类型过滤
            project_path: 项目路径过滤
            visibility: 可见性过滤
            limit: 返回数量
            offset: 跳过数量
        
        Returns:
            SearchResult 列表
        """
        if limit is None:
            limit = self.config.search_limit
        
        if limit > self.config.search_max_limit:
            limit = self.config.search_max_limit
        
        # 执行搜索
        results = self.db.search_memories(
            query=query,
            memory_type=memory_type,
            project_path=project_path,
            visibility=visibility,
            limit=limit,
            offset=offset
        )
        
        # 转换为 SearchResult
        search_results = []
        for memory, score in results:
            search_results.append(SearchResult(
                memory=memory,
                score=score,
                highlight=self._generate_highlight(memory.content, query)
            ))
        
        return search_results
    
    def search_by_tags(
        self,
        tags: List[str],
        memory_type: str = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        通过标签搜索
        
        Args:
            tags: 标签列表
            memory_type: 类型过滤
            limit: 返回数量
        
        Returns:
            SearchResult 列表
        """
        # 将标签转为搜索查询
        query = " ".join(tags)
        
        results = []
        for memory, score in self.db.search_memories(
            query=query,
            memory_type=memory_type,
            limit=limit * 2  # 多取一些
        ):
            # 检查标签匹配
            memory_tags_lower = [t.lower() for t in memory.tags]
            match_count = sum(1 for tag in tags if tag.lower() in memory_tags_lower)
            
            if match_count > 0:
                # 调整分数
                adjusted_score = score * (1 + match_count * 0.2)
                results.append(SearchResult(
                    memory=memory,
                    score=min(1.0, adjusted_score),
                    highlight=self._generate_highlight(memory.content, " ".join(tags))
                ))
        
        # 排序
        results.sort(key=lambda x: (x.score, x.memory.importance), reverse=True)
        
        return results[:limit]
    
    def get_recent(
        self,
        memory_type: str = None,
        project_path: str = None,
        limit: int = 10
    ) -> List[Memory]:
        """
        获取最近的记忆
        
        Args:
            memory_type: 类型过滤
            project_path: 项目路径过滤
            limit: 返回数量
        
        Returns:
            Memory 列表
        """
        return self.db.list_memories(
            memory_type=memory_type,
            project_path=project_path,
            limit=limit,
            offset=0
        )
    
    def get_important(
        self,
        min_importance: float = 7.0,
        limit: int = 10
    ) -> List[Memory]:
        """
        获取重要的记忆
        
        Args:
            min_importance: 最低重要性
            limit: 返回数量
        
        Returns:
            Memory 列表
        """
        # 搜索所有记忆，然后按重要性过滤
        all_memories = self.db.list_memories(limit=1000)
        
        important = [
            m for m in all_memories
            if m.importance >= min_importance
        ]
        
        important.sort(key=lambda x: (x.importance, x.created_at), reverse=True)
        
        return important[:limit]
    
    def _generate_highlight(self, content: str, query: str, max_length: int = 200) -> str:
        """
        生成高亮片段
        
        从内容中提取包含查询词的部分
        
        Args:
            content: 完整内容
            query: 查询内容
            max_length: 最大长度
        
        Returns:
            高亮片段
        """
        if not query or not content:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 查找查询词的位置
        pos = content_lower.find(query_lower)
        
        if pos == -1:
            # 没找到，返回开头
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # 计算片段起止
        start = max(0, pos - 50)
        end = min(len(content), pos + len(query) + 150)
        
        # 提取片段
        highlight = content[start:end]
        
        # 添加省略号
        if start > 0:
            highlight = "..." + highlight
        if end < len(content):
            highlight = highlight + "..."
        
        return highlight
    
    def suggest_tags(self, query: str, limit: int = 5) -> List[str]:
        """
        推荐标签
        
        根据查询推荐相关标签
        
        Args:
            query: 查询内容
            limit: 返回数量
        
        Returns:
            标签列表
        """
        # 获取所有记忆
        all_memories = self.db.list_memories(limit=500)
        
        # 收集所有标签
        tag_counts: Dict[str, int] = {}
        query_words = set(query.lower().split())
        
        for memory in all_memories:
            for tag in memory.tags:
                tag_lower = tag.lower()
                
                # 计算相关性
                relevance = sum(1 for word in query_words if word in tag_lower or tag_lower in query.lower())
                
                if relevance > 0 or not query_words:
                    if tag not in tag_counts:
                        tag_counts[tag] = 0
                    tag_counts[tag] += relevance + 1
        
        # 排序
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [tag for tag, _ in sorted_tags[:limit]]


# 全局实例
_search: Optional[SearchEngine] = None


def get_search() -> SearchEngine:
    """获取全局搜索引擎"""
    global _search
    if _search is None:
        _search = SearchEngine()
    return _search
