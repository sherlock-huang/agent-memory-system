# -*- coding: utf-8 -*-
"""
Content Review API - 内容审核技能接口
提供待审核内容列表、反馈提交等功能
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# ============================================================
# 初始化路径（在任何 src.* import 之前执行）
# ============================================================
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent.parent
_src_path = _project_root / "src"
_config_path = _project_root / "config.yaml"

# 确保 src 在 sys.path 最前面
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))


def _init_db():
    """初始化数据库连接（从环境变量读取）"""
    os.environ.setdefault('MEMORY_DB_HOST', os.getenv('MEMORY_DB_HOST', '218.201.18.131'))
    os.environ.setdefault('MEMORY_DB_PORT', os.getenv('MEMORY_DB_PORT', '8999'))
    os.environ.setdefault('MEMORY_DB_DATABASE', os.getenv('MEMORY_DB_DATABASE', 'agent_memory'))
    os.environ.setdefault('MEMORY_DB_USER', os.getenv('MEMORY_DB_USER', 'root1'))
    os.environ.setdefault('MEMORY_DB_PASSWORD', os.getenv('MEMORY_DB_PASSWORD', ''))
    
    import src.core.config as cfg_module
    cfg_module._config = None
    
    from src.core.config import Config
    cfg_module._config = Config(str(_config_path))
    
    import src.core.database as db_module
    db_module._db = None
    
    from src.core.database import Database
    return Database()


def _parse_content(memory) -> Dict[str, Any]:
    """解析记忆的 content 字段为 JSON"""
    try:
        return json.loads(memory.content)
    except (json.JSONDecodeError, TypeError):
        return {"raw": memory.content}


def list_pending_review(limit: int = 10) -> List:
    """
    列出待审核的内容
    
    Args:
        limit: 返回数量上限
        
    Returns:
        待审核的记忆列表
    """
    db = _init_db()
    
    # 搜索包含 pending_review 标签的内容
    results = db.search_memories(
        query="content:pending_review",
        limit=limit
    )
    
    return results


def list_needs_revision(limit: int = 10) -> List:
    """
    列出需要修改的内容
    
    Args:
        limit: 返回数量上限
        
    Returns:
        需要修改的记忆列表
    """
    db = _init_db()
    
    results = db.search_memories(
        query="content:needs_revision",
        limit=limit
    )
    
    return results


def list_approved(limit: int = 10) -> List:
    """
    列出已通过审核的内容
    
    Args:
        limit: 返回数量上限
        
    Returns:
        已通过的记忆列表
    """
    db = _init_db()
    
    results = db.search_memories(
        query="content:approved",
        limit=limit
    )
    
    return results


def get_content_by_id(content_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 ID 获取内容详情
    
    Args:
        content_id: 内容记忆 ID
        
    Returns:
        解析后的内容 JSON，或 None
    """
    db = _init_db()
    
    memory = db.get_memory(content_id)
    if not memory:
        return None
    
    content = _parse_content(memory)
    content['_memory_id'] = memory.id
    content['_share_title'] = memory.share_title
    content['_tags'] = memory.tags
    content['_source_agent'] = memory.source_agent
    content['_created_at'] = memory.created_at
    content['_updated_at'] = memory.updated_at
    
    return content


def get_content_full(content_id: str):
    """
    获取完整的记忆对象（包含原始 Memory 对象）
    
    Args:
        content_id: 内容记忆 ID
        
    Returns:
        Memory 对象，或 None
    """
    db = _init_db()
    return db.get_memory(content_id)


def submit_feedback(
    content_id: str,
    scores: Dict[str, float],
    issues: List[Dict[str, str]],
    summary: str,
    strengths: List[str] = None,
    approved: bool = None,
    reviewer_id: str = "shanhai"
) -> Any:
    """
    提交审核反馈
    
    Args:
        content_id: 原内容 ID
        scores: 各项评分 dict
        issues: 问题列表 [{section, issue, suggestion}]
        summary: 总体评价
        strengths: 优点列表
        approved: 是否通过（None=根据分数自动判断）
        reviewer_id: 审核人 ID
        
    Returns:
        创建的反馈 Memory 对象
    """
    # 计算综合分
    weights = {
        'title': 0.2,
        'content': 0.4,
        'cover': 0.2,
        'hashtags': 0.1,
        'platform_fit': 0.1
    }
    
    overall_score = 0.0
    for key, weight in weights.items():
        if key in scores:
            overall_score += scores[key] * weight
    
    # 自动判断是否通过
    if approved is None:
        approved = overall_score >= 7.0
    
    # 获取原内容信息
    db = _init_db()
    original = db.get_memory(content_id)
    original_title = original.share_title if original else content_id
    
    # 构建反馈 JSON
    feedback_data = {
        "original_id": content_id,
        "original_code": original_title,
        "approved": approved,
        "overall_score": round(overall_score, 1),
        "scores": {k: round(v, 1) for k, v in scores.items()},
        "strengths": strengths or [],
        "issues": issues,
        "summary": summary,
        "reviewer": reviewer_id
    }
    
    # 更新原内容状态
    new_status = "content:approved" if approved else "content:needs_revision"
    
    # 替换状态标签
    old_tags = original.tags if original else []
    new_tags = [t for t in old_tags if not t.startswith('content:')]
    new_tags.append(new_status)
    new_tags.append(f"reviewer:{reviewer_id}")
    
    if original:
        original.tags = new_tags
        db.update_memory(original)
    
    # 创建反馈记忆
    from src.core.store import StoreEngine
    
    # Reset store globals
    import src.core.store as store_module
    store_module._store = None
    
    store = StoreEngine()
    
    feedback_title = f"反馈-{original_title}"
    if original:
        # 计算修订版本号
        revision_count = len([
            t for t in old_tags 
            if t.startswith('revision:')
        ])
        new_revision = revision_count + 1
        if new_revision > 1:
            feedback_title = f"反馈-{original_title}-第{new_revision}轮"
        new_tags.append(f"revision:{new_revision}")
    
    feedback_memory = store.store(
        content=json.dumps(feedback_data, ensure_ascii=False),
        share_title=feedback_title,
        tags=["content:feedback", f"ref:{content_id}", f"reviewer:{reviewer_id}", "workflow"],
        visibility="shared",
        importance=8.0
    )
    
    return feedback_memory


def get_feedback_history(content_id: str) -> List:
    """
    获取某条内容的反馈历史
    
    Args:
        content_id: 原内容 ID
        
    Returns:
        反馈记忆列表（按时间倒序）
    """
    db = _init_db()
    
    results = db.search_memories(
        query=f"ref:{content_id} content:feedback",
        limit=20
    )
    
    # 按时间排序（最新的在前）
    results.sort(key=lambda m: m.created_at, reverse=True)
    
    return results


def approve_content(content_id: str, reviewer_id: str = "shanhai") -> bool:
    """
    直接通过内容审核
    
    Args:
        content_id: 内容 ID
        reviewer_id: 审核人 ID
        
    Returns:
        是否成功
    """
    db = _init_db()
    
    memory = db.get_memory(content_id)
    if not memory:
        return False
    
    # 更新状态标签
    new_tags = [t for t in memory.tags if not t.startswith('content:')]
    new_tags.append("content:approved")
    new_tags.append(f"reviewer:{reviewer_id}")
    memory.tags = new_tags
    
    return db.update_memory(memory)


def mark_published(content_id: str) -> bool:
    """
    标记内容已发布
    
    Args:
        content_id: 内容 ID
        
    Returns:
        是否成功
    """
    db = _init_db()
    
    memory = db.get_memory(content_id)
    if not memory:
        return False
    
    # 更新状态标签
    new_tags = [t for t in memory.tags if not t.startswith('content:')]
    new_tags.append("content:published")
    memory.tags = new_tags
    
    return db.update_memory(memory)


def list_by_platform(platform: str, status: str = None, limit: int = 20) -> List:
    """
    按平台和状态列出内容
    
    Args:
        platform: 平台名称（小红书/抖音/公众号/b站/博客）
        status: 状态筛选（可选）
        limit: 返回数量上限
        
    Returns:
        符合条件的记忆列表
    """
    db = _init_db()
    
    query_parts = [f"platform:{platform}", "workflow"]
    if status:
        query_parts.append(f"content:{status}")
    
    query = " ".join(query_parts)
    
    results = db.search_memories(query=query, limit=limit)
    
    return results


if __name__ == "__main__":
    # 简单测试
    print("Content Review API")
    print("=" * 50)
    
    # 测试列出待审核
    pending = list_pending_review(limit=5)
    print(f"\n待审核内容: {len(pending)} 条")
    for p in pending[:3]:
        print(f"  - {p.share_title} ({p.id})")
