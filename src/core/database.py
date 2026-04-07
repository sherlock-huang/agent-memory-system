# -*- coding: utf-8 -*-
"""
Database - 统一数据库入口
支持 MySQL 5.7+ / MySQL 8.0+ / SQLite
"""

from typing import Optional, Dict, Any

from .storage_adapter import StorageAdapter, SQLiteAdapter, MySQLAdapter, create_storage
from .config import Config, get_config


class Database:
    """
    统一数据库类
    根据配置自动选择合适的存储适配器
    """
    
    def __init__(self, config: Config = None):
        self.config = config or get_config()
        self._storage: Optional[StorageAdapter] = None
    
    def _init_storage(self):
        """初始化存储适配器"""
        if self._storage is None:
            db_config = self._get_db_config()
            self._storage = create_storage(db_config)
    
    def _get_db_config(self) -> Dict[str, Any]:
        """从配置中获取数据库配置"""
        # 尝试多种配置格式
        config = self.config.to_dict()
        
        # 格式 1: database.type + database.xxx
        if 'database' in config:
            db_cfg = config['database']
            if isinstance(db_cfg, dict):
                db_type = db_cfg.get('type', 'sqlite')
                if db_type == 'mysql':
                    return {
                        'type': 'mysql',
                        'host': db_cfg.get('host'),
                        'port': db_cfg.get('port', 3306),
                        'database': db_cfg.get('database'),
                        'user': db_cfg.get('user'),
                        'password': db_cfg.get('password'),
                        'charset': db_cfg.get('charset', 'utf8mb4'),
                        'pool': db_cfg.get('pool', {}),
                        'timeout': db_cfg.get('timeout', {})
                    }
                else:
                    return {
                        'type': 'sqlite',
                        'path': db_cfg.get('path', '~/.memory/memory.db')
                    }
        
        # 格式 2: type + path/host 等
        if config.get('type') == 'mysql':
            return {
                'type': 'mysql',
                'host': config.get('host'),
                'port': config.get('port', 3306),
                'database': config.get('database'),
                'user': config.get('user'),
                'password': config.get('password'),
            }
        
        # 默认 SQLite
        return {
            'type': 'sqlite',
            'path': config.get('path', '~/.memory/memory.db')
        }
    
    @property
    def storage(self) -> StorageAdapter:
        """获取存储适配器"""
        if self._storage is None:
            self._init_storage()
        return self._storage
    
    def close(self):
        """关闭连接"""
        if self._storage:
            self._storage.close()
            self._storage = None
    
    # ============================================================
    # Memory CRUD - 委托给存储适配器
    # ============================================================
    
    def insert_memory(self, memory):
        return self.storage.insert_memory(memory)
    
    def get_memory(self, memory_id: str, include_deleted: bool = False):
        return self.storage.get_memory(memory_id, include_deleted)
    
    def update_memory(self, memory):
        return self.storage.update_memory(memory)
    
    def delete_memory(self, memory_id: str, hard: bool = False):
        return self.storage.delete_memory(memory_id, hard)
    
    def restore_memory(self, memory_id: str) -> bool:
        memory = self.get_memory(memory_id, include_deleted=True)
        if not memory:
            return False
        memory.is_deleted = False
        memory.updated_at = int(time.time() * 1000)
        return self.update_memory(memory)
    
    def search_memories(self, query: str, **kwargs):
        return self.storage.search_memories(query, **kwargs)
    
    def list_memories(self, **kwargs):
        return self.storage.list_memories(**kwargs)
    
    def count_memories(self, **kwargs):
        return self.storage.count_memories(**kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        return self.storage.get_stats()


# 全局实例
_db: Optional[Database] = None


def get_db() -> Database:
    """获取全局数据库实例"""
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_db(db_path: str = None, **kwargs) -> Database:
    """
    初始化数据库
    
    Args:
        db_path: 数据库路径 (SQLite) 或连接配置 (MySQL)
        **kwargs: 其他配置参数
    """
    global _db
    
    # 使用全局配置（如果已有）
    config = get_config()
    
    if db_path:
        if db_path.startswith('mysql') or 'host' in kwargs:
            # MySQL 连接
            config.set('database.type', 'mysql')
            config.set('database.host', kwargs.get('host'))
            config.set('database.port', kwargs.get('port', 3306))
            config.set('database.database', kwargs.get('database', 'agent_memory'))
            config.set('database.user', kwargs.get('user'))
            config.set('database.password', kwargs.get('password'))
        else:
            # SQLite
            config.set('database.type', 'sqlite')
            config.set('database.path', db_path)
    
    _db = Database(config)
    return _db


def close_db():
    """关闭数据库"""
    global _db
    if _db:
        _db.close()
        _db = None


# 方便导入
import time
