# -*- coding: utf-8 -*-
"""
Content Creation API - 内容创作技能接口
提供内容存储、提交审核等功能
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
_project_root = _script_dir.parent.parent.parent  # skills/content-creation/scripts -> project root
_config_path = _project_root / "config.yaml"

# 确保项目根目录在 sys.path
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


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


def store_content(
    platform: str,
    title: str,
    content: str,
    cover_text: str = "",
    hashtags: List[str] = None,
    author_id: str = "xiao_shan",
    author_name: str = "小山",
    summary: str = ""
) -> Dict[str, Any]:
    """
    存储内容到草稿

    Args:
        platform: 平台（小红书/抖音/公众号/b站/博客）
        title: 标题
        content: 正文
        cover_text: 封面文案
        hashtags: 话题标签
        author_id: 作者 ID
        author_name: 作者显示名
        summary: 摘要

    Returns:
        包含 id 和 content 对象的字典
    """
    if hashtags is None:
        hashtags = []

    db = _init_db()

    # 构建内容 JSON
    content_data = {
        "platform": platform,
        "title": title,
        "content": content,
        "cover_text": cover_text,
        "hashtags": hashtags,
        "author": author_name,
        "summary": summary or content[:200]
    }

    # 构建标签
    tags = [
        "workflow",
        f"platform:{platform}",
        "content:draft",
        f"author:{author_id}"
    ]

    # 存储记忆
    from src.core.store import StoreEngine
    import src.core.store as store_module
    store_module._store = None

    store = StoreEngine()

    memory = store.store(
        content=json.dumps(content_data, ensure_ascii=False),
        share_title=title,
        tags=tags,
        visibility="shared",
        importance=7.0,
        source_agent=author_id,
        source_agent_name=author_name
    )

    return {
        "id": memory.id,
        "title": title,
        "platform": platform,
        "tags": tags,
        "status": "draft"
    }


def submit_for_review(
    content_id: str,
    platform: str,
    title: str,
    content: str,
    cover_text: str = "",
    hashtags: List[str] = None,
    author_id: str = "xiao_shan",
    author_name: str = "小山"
) -> Dict[str, Any]:
    """
    提交内容进入审核流程

    Args:
        content_id: 内容 ID（如果为空则先创建草稿）
        platform: 平台
        title: 标题
        content: 正文
        cover_text: 封面文案
        hashtags: 话题标签
        author_id: 作者 ID
        author_name: 作者显示名

    Returns:
        提交结果
    """
    if hashtags is None:
        hashtags = []

    db = _init_db()

    # 如果没有 content_id，先创建草稿
    if not content_id or content_id == "new":
        result = store_content(
            platform=platform,
            title=title,
            content=content,
            cover_text=cover_text,
            hashtags=hashtags,
            author_id=author_id,
            author_name=author_name
        )
        content_id = result["id"]

    # 获取现有内容
    memory = db.get_memory(content_id)
    if not memory:
        raise ValueError(f"内容不存在: {content_id}")

    # 更新标签：移除 draft，添加 pending_review
    old_tags = memory.tags or []
    new_tags = [t for t in old_tags if not t.startswith('content:')]
    new_tags.append("content:pending_review")
    new_tags.append(f"author:{author_id}")
    memory.tags = new_tags

    db.update_memory(memory)

    return {
        "id": content_id,
        "title": title,
        "platform": platform,
        "status": "pending_review",
        "message": "已提交审核，等待山海审核"
    }


def get_content_status(content_id: str) -> Optional[Dict[str, Any]]:
    """
    获取内容审核状态

    Args:
        content_id: 内容 ID

    Returns:
        状态信息
    """
    db = _init_db()
    memory = db.get_memory(content_id)

    if not memory:
        return None

    # 解析状态标签
    status = "unknown"
    for tag in (memory.tags or []):
        if tag.startswith("content:"):
            status = tag.replace("content:", "")
            break

    # 解析内容
    try:
        content_data = json.loads(memory.content)
    except:
        content_data = {"raw": memory.content}

    return {
        "id": memory.id,
        "title": memory.share_title,
        "status": status,
        "tags": memory.tags,
        "source_agent": memory.source_agent,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
        "content": content_data
    }


def list_my_drafts(author_id: str = "xiao_shan", limit: int = 10) -> List:
    """
    列出当前作者的所有草稿

    Args:
        author_id: 作者 ID
        limit: 返回数量

    Returns:
        草稿列表
    """
    db = _init_db()

    results = db.search_memories(
        query=f"author:{author_id}",
        limit=limit
    )

    # 过滤出草稿状态的
    drafts = []
    for mem in results:
        if "content:draft" in (mem.tags or []):
            drafts.append(mem)

    return drafts


def list_pending_submit(author_id: str = "xiao_shan", limit: int = 10) -> List:
    """
    列出当前作者的所有待审核内容

    Args:
        author_id: 作者 ID
        limit: 返回数量

    Returns:
        待审核内容列表
    """
    db = _init_db()

    results = db.search_memories(
        query=f"author:{author_id}",
        limit=limit
    )

    pending = []
    for mem in results:
        if "content:pending_review" in (mem.tags or []):
            pending.append(mem)

    return pending


def get_feedback_for_content(content_id: str) -> List:
    """
    获取某条内容的审核反馈

    Args:
        content_id: 原内容 ID

    Returns:
        反馈列表
    """
    from skills.content_review.scripts.api import get_feedback_history
    return get_feedback_history(content_id)


if __name__ == "__main__":
    print("Content Creation API")
    print("=" * 50)

    # 测试：列出草稿
    drafts = list_my_drafts(limit=5)
    print(f"\n我的草稿: {len(drafts)} 条")
    for d in drafts[:3]:
        print(f"  - {d.share_title} ({d.id})")
