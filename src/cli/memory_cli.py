#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory CLI - Agent 快速记忆工具 (独立版)
直接调用核心模块，无需 subprocess
"""

import sys
import json
import os
import argparse
from pathlib import Path

# 设置基础路径
# memory_cli.py 位于: agent-memory-system/src/cli/memory_cli.py
# 需要向上两级到达: agent-memory-system
_SCRIPT_DIR = Path(__file__).resolve().parent  # src/cli
_BASE_DIR = _SCRIPT_DIR.parent.parent  # agent-memory-system
_SRC_DIR = _BASE_DIR / "src"  # agent-memory-system/src

# 添加到路径
sys.path.insert(0, str(_BASE_DIR))

# 切换工作目录
os.chdir(str(_BASE_DIR))

# 版本
__version__ = "1.0.0"

# 导入核心模块
from src.core import init_config, init_db, get_store, get_search, get_db, close_db
from src.core.models import MemoryType, Visibility


def get_memory_dir() -> Path:
    """获取记忆存储目录"""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home()
    return base / ".memory"


def get_config_path() -> Path:
    """获取配置文件路径"""
    # 优先使用脚本目录下的配置
    local_config = _BASE_DIR / "config.yaml"
    if local_config.exists():
        return local_config
    return get_memory_dir() / "config.yaml"


# ============================================================
# CLI 入口
# ============================================================

def cmd_store(args) -> dict:
    """store 命令"""
    store = get_store()
    
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]
    
    memory = store.store(
        content=args.content,
        memory_type=args.type,
        visibility=args.visibility,
        tags=tags,
        importance=args.importance,
        project_path=args.project,
    )
    
    return {
        "status": "stored",
        "id": memory.id,
        "type": memory.type,
        "visibility": memory.visibility,
        "importance": memory.importance,
        "tags": memory.tags,
        "created_at": memory.created_at
    }


def cmd_search(args) -> dict:
    """search 命令"""
    search = get_search()
    
    results = search.search(
        query=args.query,
        memory_type=args.type,
        project_path=args.project,
        limit=args.limit
    )
    
    # 转换结果为 JSON 可序列化格式
    def convert_result(r):
        d = r.to_dict()
        # 确保所有数值类型可序列化
        for k, v in d.items():
            if isinstance(v, (int, float)):
                d[k] = float(v) if isinstance(v, float) else v
        return d
    
    return {
        "status": "ok",
        "query": args.query,
        "count": len(results),
        "results": [convert_result(r) for r in results]
    }


def cmd_get(args) -> dict:
    """get 命令"""
    store = get_store()
    
    memory = store.get(args.id)
    
    if not memory:
        return {"status": "error", "message": "Memory not found"}
    
    return {
        "status": "ok",
        "memory": memory.to_dict()
    }


def cmd_list(args) -> dict:
    """list 命令"""
    store = get_store()
    
    memories = store.list(
        memory_type=args.type,
        project_path=args.project,
        limit=args.limit,
        offset=args.offset
    )
    
    total = store.count(
        memory_type=args.type,
        project_path=args.project
    )
    
    return {
        "status": "ok",
        "total": total,
        "count": len(memories),
        "memories": [m.to_dict() for m in memories]
    }


def cmd_delete(args) -> dict:
    """delete 命令"""
    store = get_store()
    
    success = store.delete(args.id, hard=args.hard)
    
    if not success:
        return {"status": "error", "message": "Memory not found or permission denied"}
    
    return {
        "status": "deleted",
        "id": args.id,
        "hard": args.hard
    }


def cmd_status(args) -> dict:
    """status 命令"""
    store = get_store()
    stats = store.stats()
    
    # 转换 stats 为 JSON 可序列化类型
    def convert_stats(s):
        if s is None:
            return 0
        # 处理 Decimal 类型
        try:
            from decimal import Decimal
            if isinstance(s, Decimal):
                return int(s) if s == int(s) else float(s)
        except ImportError:
            pass
        if isinstance(s, (int, float)):
            return int(s) if s == int(s) else float(s)
        return s
    
    stats = {k: convert_stats(v) for k, v in stats.items()}
    
    # 获取数据库信息
    db = get_db()
    db_info = {
        "type": type(db.storage).__name__,
    }
    
    if hasattr(db.storage, 'db_path'):
        db_info["path"] = str(db.storage.db_path)
    elif hasattr(db.storage, 'config'):
        db_info["host"] = db.storage.config.get('host', 'unknown')
    
    return {
        "status": "ok",
        "version": __version__,
        "database": db_info,
        "memory_dir": str(get_memory_dir()),
        "stats": stats
    }


def cmd_tags(args) -> dict:
    """tags 命令"""
    store = get_store()
    
    memories = store.list(limit=500)
    
    tag_counts = {}
    for m in memories:
        for tag in m.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "status": "ok",
        "count": len(sorted_tags),
        "tags": [{"tag": t, "count": c} for t, c in sorted_tags]
    }


# ========== 经验分享命令 ==========

def cmd_share_experience(args) -> dict:
    """
    share-experience 命令 - 创建并分享经验到云端

    用户必须提供:
    - title: 经验名称（唯一）
    - content: 经验正文（MD格式）

    可选:
    - summary: 摘要
    - notes: 备注
    - tags: 标签
    - importance: 重要性
    """
    store = get_store()

    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    # 创建经验记忆（visibility 固定为 shared）
    memory = store.store(
        content=args.content,
        memory_type=args.type or "knowledge",
        visibility="shared",  # 经验默认 shared
        tags=tags,
        importance=args.importance or 7.0,
        project_path=args.project,
        # 经验专属字段
        share_title=args.title,
        md_content=args.content,  # MD 格式正文
        notes=args.notes,
        summary=args.summary,
    )

    return {
        "status": "shared",
        "action": "share_experience",
        "id": memory.id,
        "title": memory.share_title,
        "visibility": memory.visibility,
        "markdown": memory.to_markdown(),
        "message": "经验已分享到云端，其他AI可查询"
    }


def cmd_cloud_query(args) -> dict:
    """
    cloud-query 命令 - 查询云端他人经验

    只查询有经验名称(share_title)的 shared/global 记忆
    """
    search = get_search()

    results = search.search(
        query=args.query,
        memory_type=args.type if hasattr(args, 'type') and args.type else None,
        limit=args.limit * 2  # 多取一些，因为要过滤
    )

    # 过滤只保留有经验名称的记忆（才是真正的经验）
    cloud_results = [r for r in results if r.memory.is_experience()]

    # 转换结果
    def convert_result(r):
        d = r.to_dict()
        for k, v in d.items():
            if isinstance(v, (int, float)):
                d[k] = float(v) if isinstance(v, float) else v
        # 添加 markdown 格式输出
        d['markdown'] = r.memory.to_markdown()
        return d

    return {
        "status": "ok",
        "query": args.query,
        "source": "cloud_experiences",
        "count": len(cloud_results[:args.limit]),
        "results": [convert_result(r) for r in cloud_results[:args.limit]]
    }


def cmd_list_shared(args) -> dict:
    """
    list-shared 命令 - 列出所有共享记忆
    """
    store = get_store()

    # 列出所有 shared/global 记忆
    all_memories = store.list(limit=args.limit)

    shared = [m for m in all_memories if m.visibility in ['shared', 'global']]

    return {
        "status": "ok",
        "source": "cloud_shared",
        "count": len(shared),
        "memories": [m.to_dict() for m in shared]
    }


def cmd_my_experiences(args) -> dict:
    """
    my-experiences 命令 - 获取我分享过的经验
    """
    store = get_store()

    memories = store.list(limit=args.limit)

    # 获取本机分享过的经验（shared/global 且有 share_title）
    mine = [m for m in memories if m.visibility in ['shared', 'global'] and m.is_experience()]

    return {
        "status": "ok",
        "count": len(mine),
        "experiences": [
            {
                **m.to_dict(),
                "markdown": m.to_markdown()
            }
            for m in mine
        ]
    }


def cmd_sync(args) -> dict:
    """
    sync 命令 - 双向同步

    push: 将本机 shared/global 记忆同步到云端（实际上就是标记为 shared）
    pull: 从云端获取新的共享记忆（实际上就是查询 shared/global）
    both: 两者都做
    """
    direction = args.direction

    results = {}

    if direction in ['push', 'both']:
        # Push: 将本机 shared/global 记忆同步（只是确保状态正确）
        store = get_store()
        all_mem = store.list(limit=1000)
        shared = [m for m in all_mem if m.visibility in ['shared', 'global']]
        results['pushed'] = len(shared)

    if direction in ['pull', 'both']:
        # Pull: 获取云端共享记忆
        store = get_store()
        all_mem = store.list(limit=1000)
        shared = [m for m in all_mem if m.visibility in ['shared', 'global']]
        results['pulled'] = len(shared)

    return {
        "status": "synced",
        "direction": direction,
        "results": results
    }


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog='memory',
        description=f'Memory CLI v{__version__} - Agent 快速记忆工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  memory store "内容..." --type project --tags python,fastapi
  memory search "python" --limit 5
  memory list --type project
  memory get mem_abc123
  memory status
  memory tags
        """
    )
    
    # 全局选项
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--quiet', '-q', action='store_true', help='简洁输出')
    parser.add_argument('--format', '-f', choices=['json', 'table'], default='json', help='输出格式')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # store 命令
    store_parser = subparsers.add_parser('store', aliases=['s', 'add'], help='存储记忆')
    store_parser.add_argument('content', help='记忆内容')
    store_parser.add_argument('--type', '-t', 
                              default='general',
                              choices=['general', 'project', 'preference', 'knowledge', 'team'],
                              help='记忆类型')
    store_parser.add_argument('--visibility', '-v',
                              default='shared',
                              choices=['private', 'shared', 'global'],
                              help='可见性')
    store_parser.add_argument('--tags', '-g', help='标签，逗号分隔')
    store_parser.add_argument('--importance', '-i', type=float, default=5.0,
                              help='重要性 1-10')
    store_parser.add_argument('--project', '-p', help='项目路径')
    
    # search 命令
    search_parser = subparsers.add_parser('search', aliases=['find'], help='搜索记忆')
    search_parser.add_argument('query', help='搜索内容')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='返回数量')
    search_parser.add_argument('--type', '-t', help='记忆类型')
    search_parser.add_argument('--project', '-p', help='项目路径')
    
    # get 命令
    get_parser = subparsers.add_parser('get', aliases=['g'], help='获取记忆')
    get_parser.add_argument('id', help='记忆 ID')
    
    # list 命令
    list_parser = subparsers.add_parser('list', aliases=['ls', 'l'], help='列出记忆')
    list_parser.add_argument('--type', '-t', help='记忆类型')
    list_parser.add_argument('--project', '-p', help='项目路径')
    list_parser.add_argument('--limit', '-l', type=int, default=50)
    list_parser.add_argument('--offset', '-o', type=int, default=0)
    
    # delete 命令
    delete_parser = subparsers.add_parser('delete', aliases=['rm', 'd'], help='删除记忆')
    delete_parser.add_argument('id', help='记忆 ID')
    delete_parser.add_argument('--hard', action='store_true', help='永久删除')
    
    # status 命令
    subparsers.add_parser('status', aliases=['st'], help='状态')
    
    # tags 命令
    subparsers.add_parser('tags', help='列出所有标签')

    # ========== 经验分享命令 ==========

    # share-experience 命令 - 创建并分享经验（必须指定标题和内容）
    share_exp_parser = subparsers.add_parser('share-experience', aliases=['share', 'push', 'exp'],
                                              help='创建并分享经验到云端（需指定标题和内容）')
    share_exp_parser.add_argument('--title', '-t', required=True, help='经验名称（唯一标题）')
    share_exp_parser.add_argument('content', help='经验正文（MD格式）')
    share_exp_parser.add_argument('--summary', '-s', help='摘要（一句话概括）')
    share_exp_parser.add_argument('--notes', '-n', help='备注（适用场景、注意事项等）')
    share_exp_parser.add_argument('--tags', '-g', help='标签，逗号分隔')
    share_exp_parser.add_argument('--importance', '-i', type=float, default=7.0,
                                 help='重要性 1-10 (default: 7.0)')
    share_exp_parser.add_argument('--type', '-y', default='knowledge', help='记忆类型')
    share_exp_parser.add_argument('--project', '-p', help='项目路径')

    # cloud-query 命令
    cloud_query_parser = subparsers.add_parser('cloud-query', aliases=['cq', 'cloud'],
                                               help='查询云端他人经验')
    cloud_query_parser.add_argument('query', help='查询内容')
    cloud_query_parser.add_argument('--limit', '-l', type=int, default=10)
    cloud_query_parser.add_argument('--type', '-t', help='记忆类型')
    cloud_query_parser.add_argument('--tags', '-g', help='标签过滤')

    # list-shared 命令
    list_shared_parser = subparsers.add_parser('list-shared', aliases=['ls-shared'],
                                                help='列出所有共享记忆')
    list_shared_parser.add_argument('--limit', '-l', type=int, default=50)

    # my-experiences 命令
    my_exp_parser = subparsers.add_parser('my-experiences', aliases=['mine', 'my'],
                                          help='获取我分享过的经验')
    my_exp_parser.add_argument('--limit', '-l', type=int, default=50)

    # sync 命令
    sync_parser = subparsers.add_parser('sync', aliases=['sync-memories'],
                                        help='双向同步记忆')
    sync_parser.add_argument('--direction', '-d',
                            choices=['push', 'pull', 'both'],
                            default='both',
                            help='同步方向 (default: both)')

    args = parser.parse_args()
    
    # 无命令时显示 help
    if not args.command:
        parser.print_help()
        return
    
    # 初始化
    try:
        # 确保目录存在
        get_memory_dir().mkdir(parents=True, exist_ok=True)
        
        # 尝试加载配置文件
        config_path = get_config_path()
        if config_path.exists():
            init_config(config_path=str(config_path))
        else:
            init_config()
        
        # 初始化数据库
        init_db()
        
        # 执行命令
        if args.command in ['store', 's', 'add']:
            result = cmd_store(args)
        elif args.command in ['search', 's', 'find']:
            result = cmd_search(args)
        elif args.command in ['get', 'g']:
            result = cmd_get(args)
        elif args.command in ['list', 'ls', 'l']:
            result = cmd_list(args)
        elif args.command in ['delete', 'rm', 'd']:
            result = cmd_delete(args)
        elif args.command in ['status', 'st']:
            result = cmd_status(args)
        elif args.command == 'tags':
            result = cmd_tags(args)
        # 经验分享命令
        elif args.command in ['share-experience', 'share', 'push', 'exp']:
            result = cmd_share_experience(args)
        elif args.command in ['cloud-query', 'cq', 'cloud']:
            result = cmd_cloud_query(args)
        elif args.command in ['list-shared', 'ls-shared']:
            result = cmd_list_shared(args)
        elif args.command in ['my-experiences', 'mine', 'my']:
            result = cmd_my_experiences(args)
        elif args.command in ['sync', 'sync-memories']:
            result = cmd_sync(args)
        else:
            parser.print_help()
            return
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        if args.debug:
            raise
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    finally:
        close_db()


if __name__ == '__main__':
    main()
