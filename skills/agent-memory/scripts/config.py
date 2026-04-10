# -*- coding: utf-8 -*-
"""
Agent Memory Skill - Configuration
配置管理：支持环境变量，不明文存储密码
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class Config:
    """
    配置管理类
    
    优先级：
    1. 环境变量 (最高)
    2. 配置文件 (config.yaml)
    3. 默认值
    """
    
    # 环境变量前缀
    ENV_PREFIX = "MEMORY_DB_"
    
    # 默认配置
    DEFAULTS = {
        "host": "localhost",
        "port": 3306,
        "database": "agent_memory",
        "user": "",
        "password": "",
        "charset": "utf8mb4",
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = {}
        self._config_path = config_path or self._find_config_path()
        self._load()
    
    def _find_config_path(self) -> Optional[str]:
        """查找配置文件"""
        candidates = [
            # 项目根目录
            Path(__file__).parent.parent.parent.parent / "config.yaml",
            # workspace 配置
            Path.home() / ".openclaw" / "workspace" / "agent-memory-system" / "config.yaml",
            # 当前目录
            Path.cwd() / "config.yaml",
        ]
        
        for p in candidates:
            if p.exists():
                return str(p)
        
        return None
    
    def _load(self):
        """加载配置"""
        # 1. 加载默认配置
        self._config = self.DEFAULTS.copy()
        
        # 2. 从文件加载（会解析 ${ENV_VAR} 格式）
        if self._config_path and Path(self._config_path).exists():
            self._load_file(self._config_path)
        
        # 3. 环境变量覆盖（最高优先级）
        self._load_env()
    
    def _load_file(self, path: str):
        """从 YAML 文件加载配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data and 'database' in data:
                db_config = data.get('database', {})
                for key, value in db_config.items():
                    if isinstance(value, str):
                        # 解析环境变量引用 ${VAR_NAME} 或 ${VAR_NAME:-default}
                        value = self._resolve_env_var(value)
                    self._config[key] = value
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}", file=sys.stderr)
    
    def _resolve_env_var(self, value: str) -> str:
        """解析环境变量引用
        
        支持格式：
        - ${ENV_VAR_NAME}
        - ${ENV_VAR_NAME:-default_value}
        """
        if not isinstance(value, str):
            return value
        
        import re
        
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replace(match):
            var_name = match.group(1)
            default = match.group(2)  # 可能为 None
            
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default is not None:
                return default
            else:
                return match.group(0)  # 返回原字符串
        
        return re.sub(pattern, replace, value)
    
    def _load_env(self):
        """从环境变量加载配置"""
        env_mappings = {
            f"{self.ENV_PREFIX}HOST": "host",
            f"{self.ENV_PREFIX}PORT": "port",
            f"{self.ENV_PREFIX}DATABASE": "database",
            f"{self.ENV_PREFIX}USER": "user",
            f"{self.ENV_PREFIX}PASSWORD": "password",
            f"{self.ENV_PREFIX}CHARSET": "charset",
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 类型转换
                if config_key == "port":
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        env_value = 3306
                self._config[config_key] = env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)
    
    @property
    def host(self) -> str:
        return self.get("host", "localhost")
    
    @property
    def port(self) -> int:
        return int(self.get("port", 3306))
    
    @property
    def database(self) -> str:
        return self.get("database", "agent_memory")
    
    @property
    def user(self) -> str:
        return self.get("user", "")
    
    @property
    def password(self) -> str:
        return self.get("password", "")
    
    @property
    def charset(self) -> str:
        return self.get("charset", "utf8mb4")
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置（必须有 host, user, password）"""
        return bool(self.host and self.user and self.password)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._config.copy()
    
    def __repr__(self) -> str:
        return f"<Config host={self.host} port={self.port} database={self.database} user={self.user}>"


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置"""
    global _config
    _config = Config(config_path)
    return _config


def require_config() -> Config:
    """
    获取配置，如果未配置则抛出异常
    调用方应该捕获此异常并提示用户配置
    """
    config = get_config()
    if not config.is_configured:
        raise ConfigurationError(
            "数据库未配置。请提供以下信息：\n"
            "1. MEMORY_DB_HOST - 数据库地址\n"
            "2. MEMORY_DB_PORT - 端口（默认3306）\n"
            "3. MEMORY_DB_DATABASE - 数据库名（默认agent_memory）\n"
            "4. MEMORY_DB_USER - 用户名\n"
            "5. MEMORY_DB_PASSWORD - 密码\n\n"
            "设置方式（PowerShell）：\n"
            "$env:MEMORY_DB_HOST = 'your-host.com'\n"
            "$env:MEMORY_DB_PASSWORD = 'your-password'"
        )
    return config


class ConfigurationError(Exception):
    """配置错误异常"""
    pass
