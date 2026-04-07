#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Test Script - 快速测试脚本
测试数据库连接和基本功能
"""

import sys
import os
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core import init_config, init_db, get_db, get_store, get_search, close_db
from core.models import MemoryType, Visibility


def test_connection():
    """测试数据库连接"""
    print("[1] 测试数据库连接...")
    
    # 尝试从配置文件加载
    config_path = Path(__file__).parent / 'config.yaml'
    
    if config_path.exists():
        print(f"    找到配置文件: {config_path}")
        init_config(config_path=str(config_path))
    else:
        print("    未找到配置文件，使用默认 SQLite")
        init_config()
    
    db = init_db()
    print(f"    数据库类型: {type(db.storage).__name__}")
    print(f"    数据库路径: {db.storage.db_path if hasattr(db.storage, 'db_path') else 'MySQL'}")
    print("    ✓ 连接成功")
    return db


def test_crud(db):
    """测试 CRUD 操作"""
    print("\n[2] 测试 CRUD 操作...")
    
    store = get_store()
    
    # 存储
    print("    存储记忆...")
    memory = store.store(
        content="这是测试记忆 - This is a test memory",
        memory_type="project",
        tags=["test", "python"],
        importance=7.0
    )
    print(f"    ✓ 存储成功: {memory.id}")
    
    # 获取
    print("    获取记忆...")
    retrieved = store.get(memory.id)
    assert retrieved is not None
    assert retrieved.content == memory.content
    print(f"    ✓ 获取成功: {retrieved.id}")
    
    # 更新
    print("    更新记忆...")
    updated = store.update(memory.id, importance=9.0)
    assert updated.importance == 9.0
    print(f"    ✓ 更新成功")
    
    # 搜索
    print("    搜索记忆...")
    results = store.list(memory_type="project")
    assert len(results) > 0
    print(f"    ✓ 搜索成功: 找到 {len(results)} 条")
    
    # 删除
    print("    删除记忆...")
    success = store.delete(memory.id)
    assert success
    print(f"    ✓ 删除成功")
    
    return True


def test_stats(db):
    """测试统计"""
    print("\n[3] 测试统计功能...")
    
    store = get_store()
    
    # 添加一些测试数据
    for i in range(3):
        store.store(
            content=f"测试记忆 {i}",
            memory_type="project",
            importance=5.0 + i
        )
    
    stats = store.stats()
    print(f"    总数: {stats.get('total', 0)}")
    print(f"    项目: {stats.get('projects', 0)}")
    print("    ✓ 统计正常")


def main():
    print("=" * 50)
    print("  Agent Memory System - 快速测试")
    print("=" * 50)
    
    db = None
    try:
        db = test_connection()
        test_crud(db)
        test_stats(db)
        
        print("\n" + "=" * 50)
        print("  ✓ 所有测试通过!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if db:
            close_db()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
