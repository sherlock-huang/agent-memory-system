# -*- coding: utf-8 -*-
"""
Memory System Configuration
配置管理模块
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "db_path": None,  # None means auto-detect
        "db_name": "memory.db",
        
        "search": {
            "default_limit": 10,
            "max_limit": 100,
            "min_score": 0.3,
        },
        
        "embedding": {
            "provider": "local",  # local | openai | ollama
            "model": "nomic-embed-text",
            "dimension": 1536,
            "openai_api_key": None,
            "openai_base_url": "https://api.openai.com/v1",
            "ollama_base_url": "http://localhost:11434",
        },
        
        "source": "cli",  # 默认来源
        "agent_id": None,
        
        "logging": {
            "level": "INFO",
            "file": None,  # None means auto-detect
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self._config_path = config_path
        self._load()
    
    def _get_memory_dir(self) -> Path:
        """获取记忆存储目录"""
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        else:
            base = Path.home()
        
        memory_dir = base / ".memory"
        return memory_dir
    
    def _get_default_db_path(self) -> Path:
        """获取默认数据库路径"""
        memory_dir = self._get_memory_dir()
        db_name = self._config.get("db_name", "memory.db")
        return memory_dir / db_name
    
    def _load(self):
        """加载配置"""
        # 1. 环境变量覆盖
        if os.getenv("MEMORY_DB_PATH"):
            self._config["db_path"] = os.getenv("MEMORY_DB_PATH")
        
        if os.getenv("MEMORY_SOURCE"):
            self._config["source"] = os.getenv("MEMORY_SOURCE")
        
        if os.getenv("MEMORY_AGENT_ID"):
            self._config["agent_id"] = os.getenv("MEMORY_AGENT_ID")
        
        if os.getenv("OPENAI_API_KEY"):
            self._config["embedding"]["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        
        # 2. 配置文件覆盖
        config_paths = [
            self._config_path,
            self._get_memory_dir() / "config.json",
            self._get_memory_dir() / "config.yaml",
            Path.home() / ".memory" / "config.json",
            Path.home() / ".memory" / "config.yaml",
        ]
        
        for path in config_paths:
            if path and Path(path).exists():
                self._load_file(Path(path))
                break
        
        # 3. 设置默认值
        if self._config.get("db_path") is None:
            self._config["db_path"] = str(self._get_default_db_path())
        
        if self._config.get("agent_id") is None:
            self._config["agent_id"] = f"{self._config['source']}_{os.getenv('USER', 'default')}"
        
        # 4. 确保目录存在
        db_path = Path(self._config["db_path"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_file(self, path: Path):
        """从文件加载配置"""
        try:
            if path.suffix == ".json":
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._merge_config(data)
            elif path.suffix in (".yaml", ".yml"):
                import yaml
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._merge_config(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}", file=sys.stderr)
    
    def _resolve_env_vars(self, value: Any) -> Any:
        """解析环境变量引用
        
        支持格式:
        - ${ENV_VAR_NAME} - 基本格式
        - ${ENV_VAR_NAME:-default} - 带默认值
        - $ENV_VAR_NAME - 简写格式（不推荐）
        """
        if not isinstance(value, str):
            return value
        
        import re
        
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:-default} 或 $VAR_NAME
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}|$([A-Z_][A-Z0-9_]*)'
        
        def replace_env_var(match):
            # ${VAR_NAME} 或 ${VAR_NAME:-default}
            if match.group(1) is not None:
                var_name = match.group(1)
                default_value = match.group(2)  # 可能为 None
                env_value = os.getenv(var_name)
                if env_value is not None:
                    return env_value
                elif default_value is not None:
                    return default_value
                else:
                    return match.group(0)  # 返回原字符串
            # $VAR_NAME
            elif match.group(3) is not None:
                var_name = match.group(3)
                env_value = os.getenv(var_name)
                return env_value if env_value is not None else match.group(0)
            return match.group(0)
        
        result = re.sub(pattern, replace_env_var, value)
        
        return result
    
    def _merge_config(self, data: Dict[str, Any]):
        """合并配置（深度合并）"""
        def merge(target: Dict, source: Dict):
            for key, value in source.items():
                # 如果 value 是字符串，检查是否包含环境变量引用
                if isinstance(value, str):
                    value = self._resolve_env_vars(value)
                elif isinstance(value, dict):
                    # 递归处理字典
                    if key not in target:
                        target[key] = {}
                    if isinstance(target[key], dict):
                        merge(target[key], value)
                    else:
                        target[key] = value
                    continue
                
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge(target[key], value)
                else:
                    target[key] = value
        
        merge(self._config, data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split(".")
        target = self._config
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    @property
    def db_path(self) -> str:
        """数据库路径"""
        return str(self._config["db_path"])
    
    @property
    def source(self) -> str:
        """来源标识"""
        return self._config["source"]
    
    @property
    def agent_id(self) -> str:
        """Agent ID"""
        return self._config["agent_id"]
    
    @property
    def search_limit(self) -> int:
        """默认搜索限制"""
        return self.get("search.default_limit", 10)
    
    @property
    def search_max_limit(self) -> int:
        """最大搜索限制"""
        return self.get("search.max_limit", 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._config.copy()


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(**kwargs) -> Config:
    """初始化配置"""
    global _config
    if _config is not None and not kwargs:
        # 如果已有配置且没有新参数，返回现有配置
        return _config
    _config = Config(**kwargs)
    return _config
