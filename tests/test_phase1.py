# -*- coding: utf-8 -*-
"""
Phase 1 Tests - Core Database and Store

运行方式:
    cd agent-memory-system
    python -m pytest tests/test_phase1.py -v
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import init_config, init_db, get_db, get_store, get_search, close_db
from src.core.database import Database
from src.core.models import Memory, MemoryType, Visibility


@pytest.fixture(scope="function")
def temp_db():
    """创建临时数据库"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_memory.db")
    
    # 初始化
    init_config()
    init_db(db_path)
    
    yield db_path
    
    # 清理
    close_db()
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDatabase:
    """数据库测试"""
    
    def test_init(self, temp_db):
        """测试数据库初始化"""
        db = get_db()
        assert db is not None
        assert db.db_path.exists()
    
    def test_insert_memory(self, temp_db):
        """测试插入记忆"""
        db = get_db()
        
        memory = Memory(
            content="Test memory content",
            type=MemoryType.PROJECT.value,
            visibility=Visibility.SHARED.value,
            importance=7.0,
            tags=["test", "pytest"]
        )
        
        db.insert_memory(memory)
        
        # 验证
        retrieved = db.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory content"
        assert retrieved.type == "project"
        assert retrieved.importance == 7.0
        assert "test" in retrieved.tags
    
    def test_get_memory(self, temp_db):
        """测试获取记忆"""
        db = get_db()
        
        memory = Memory(content="Test content")
        db.insert_memory(memory)
        
        # 存在
        result = db.get_memory(memory.id)
        assert result is not None
        assert result.id == memory.id
        
        # 不存在
        result = db.get_memory("non_existent_id")
        assert result is None
    
    def test_update_memory(self, temp_db):
        """测试更新记忆"""
        db = get_db()
        
        memory = Memory(content="Original content", importance=5.0)
        db.insert_memory(memory)
        
        # 更新
        memory.content = "Updated content"
        memory.importance = 9.0
        db.update_memory(memory)
        
        # 验证
        retrieved = db.get_memory(memory.id)
        assert retrieved.content == "Updated content"
        assert retrieved.importance == 9.0
    
    def test_delete_memory(self, temp_db):
        """测试删除记忆"""
        db = get_db()
        
        memory = Memory(content="To be deleted")
        db.insert_memory(memory)
        
        # 软删除
        db.delete_memory(memory.id)
        assert db.get_memory(memory.id) is None
        
        # 硬删除
        memory2 = Memory(content="To be hard deleted")
        db.insert_memory(memory2)
        db.delete_memory(memory2.id, hard=True)
        
        # 永久删除后无法恢复
        rows = db.fetchall("SELECT * FROM memories WHERE id = ?", (memory2.id,))
        assert len(rows) == 0
    
    def test_search_memories(self, temp_db):
        """测试搜索记忆"""
        db = get_db()
        
        # 插入多条记忆
        memories = [
            Memory(content="Python is great", type="project", importance=8.0, tags=["python"]),
            Memory(content="JavaScript is also great", type="project", importance=7.0, tags=["javascript"]),
            Memory(content="I prefer Python over JavaScript", type="preference", importance=9.0, tags=["python", "preference"]),
        ]
        
        for m in memories:
            db.insert_memory(m)
        
        # 搜索 Python
        results = db.search_memories(query="Python")
        assert len(results) >= 2
        
        # 搜索并按分数排序
        results = db.search_memories(query="Python", memory_type="project")
        assert all(r[0].type == "project" for r in results)


class TestStoreEngine:
    """存储引擎测试"""
    
    def test_store(self, temp_db):
        """测试存储"""
        store = get_store()
        
        memory = store.store(
            content="This is a test memory",
            memory_type="project",
            tags=["test"]
        )
        
        assert memory.id.startswith("mem_")
        assert memory.content == "This is a test memory"
        assert memory.type == "project"
        assert memory.tags == ["test"]
    
    def test_store_with_auto_summary(self, temp_db):
        """测试自动摘要"""
        store = get_store()
        
        # 长内容应该自动生成摘要
        long_content = "A" * 300
        memory = store.store(content=long_content)
        
        assert memory.summary is not None
        assert len(memory.summary) < len(long_content)
    
    def test_store_validation(self, temp_db):
        """测试验证"""
        store = get_store()
        
        # 空内容应该报错
        with pytest.raises(ValueError):
            store.store(content="")
        
        # 无效的重要性应该报错
        with pytest.raises(ValueError):
            store.store(content="Test", importance=15)
        
        with pytest.raises(ValueError):
            store.store(content="Test", importance=0)
    
    def test_update(self, temp_db):
        """测试更新"""
        store = get_store()
        
        memory = store.store(content="Original")
        updated = store.update(memory.id, content="Updated", importance=10)
        
        assert updated.content == "Updated"
        assert updated.importance == 10
    
    def test_delete_and_restore(self, temp_db):
        """测试删除和恢复"""
        store = get_store()
        
        memory = store.store(content="To be restored")
        store.delete(memory.id)
        
        # 软删除后应该找不到
        assert store.get(memory.id) is None
        
        # 恢复
        success = store.restore(memory.id)
        assert success is True
        assert store.get(memory.id) is not None
    
    def test_list(self, temp_db):
        """测试列表"""
        store = get_store()
        
        # 插入多条
        for i in range(5):
            store.store(content=f"Memory {i}", type="project")
        
        # 列出
        memories = store.list(memory_type="project")
        assert len(memories) >= 5
        
        # 统计
        count = store.count(memory_type="project")
        assert count >= 5
    
    def test_stats(self, temp_db):
        """测试统计"""
        store = get_store()
        
        store.store(content="Project 1", type="project")
        store.store(content="Project 2", type="project")
        store.store(content="Preference", type="preference")
        
        stats = store.stats()
        
        assert stats['total'] >= 3
        assert stats['projects'] >= 2
        assert stats['preferences'] >= 1


class TestSearchEngine:
    """搜索引擎测试"""
    
    def test_search(self, temp_db):
        """测试搜索"""
        store = get_store()
        search = get_search()
        
        # 添加记忆
        store.store(content="Python FastAPI web framework", type="project", tags=["python", "fastapi"])
        store.store(content="JavaScript Node.js backend", type="project", tags=["javascript", "nodejs"])
        store.store(content="I love Python programming", type="preference", tags=["python", "love"])
        
        # 搜索
        results = search.search(query="Python")
        assert len(results) >= 2
        
        # 验证返回的是 SearchResult
        assert all(hasattr(r, 'score') for r in results)
    
    def test_search_with_filter(self, temp_db):
        """测试过滤搜索"""
        store = get_store()
        search = get_search()
        
        store.store(content="Project memory", type="project")
        store.store(content="Preference memory", type="preference")
        
        # 只搜索 project 类型
        results = search.search(query="memory", memory_type="project")
        assert all(r.memory.type == "project" for r in results)
    
    def test_get_recent(self, temp_db):
        """测试获取最近记忆"""
        store = get_store()
        search = get_search()
        
        for i in range(3):
            store.store(content=f"Recent {i}")
        
        recent = search.get_recent(limit=2)
        assert len(recent) <= 2
    
    def test_get_important(self, temp_db):
        """测试获取重要记忆"""
        store = get_store()
        search = get_search()
        
        store.store(content="Important", importance=9.0)
        store.store(content="Normal", importance=5.0)
        
        important = search.get_important(min_importance=8.0)
        assert all(m.importance >= 8.0 for m in important)


class TestMemoryModel:
    """记忆模型测试"""
    
    def test_memory_creation(self):
        """测试记忆创建"""
        memory = Memory(content="Test")
        
        assert memory.id.startswith("mem_")
        assert memory.content == "Test"
        assert memory.type == "general"
        assert memory.visibility == "shared"
        assert memory.importance == 5.0
        assert memory.tags == []
        assert memory.is_deleted is False
    
    def test_memory_to_dict(self):
        """测试转字典"""
        memory = Memory(
            content="Test",
            type="project",
            tags=["test"]
        )
        
        d = memory.to_dict()
        
        assert d['content'] == "Test"
        assert d['type'] == "project"
        assert d['tags'] == ["test"]
        assert 'id' in d
        assert 'created_at' in d
    
    def test_memory_from_dict(self):
        """测试从字典创建"""
        d = {
            'id': 'mem_test123',
            'content': 'Test',
            'type': 'project',
            'tags': '["test"]',  # JSON string
            'created_at': 1234567890,
            'updated_at': 1234567890,
            'is_deleted': False
        }
        
        memory = Memory.from_dict(d)
        
        assert memory.id == 'mem_test123'
        assert memory.content == 'Test'
        assert memory.tags == ["test"]
    
    def test_memory_soft_delete(self):
        """测试软删除"""
        memory = Memory(content="Test")
        assert memory.is_deleted is False
        
        memory.soft_delete()
        assert memory.is_deleted is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
