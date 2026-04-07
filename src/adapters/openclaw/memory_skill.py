#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Memory Skill - Python Wrapper
OpenClaw 调用记忆系统的桥接模块

支持功能:
1. 存储记忆 - store()
2. 搜索记忆 - search()
3. 分享经验到云端 - share_experience()
4. 查询他人经验 - query_cloud_experience()
5. 双向同步 - sync()
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

# 记忆系统路径
MEMORY_SYSTEM_PATH = Path(__file__).parent.parent.parent.parent
CLI_PATH = MEMORY_SYSTEM_PATH / "src" / "cli" / "memory_cli.py"


class MemorySkill:
    """
    OpenClaw Memory Skill
    提供给 OpenClaw 调用的 Python API
    """
    
    def __init__(self, config_path: str = None):
        self.cli_path = str(CLI_PATH)
        self.config_path = config_path or self._find_config()
        
        # 设置 Python 路径
        self.python_path = self._find_python()
    
    def _find_python(self) -> str:
        """查找 Python 解释器"""
        # 常见路径
        candidates = [
            "C:\\Users\\openclaw-windows-2\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
            "python",
            "python3",
        ]
        
        for cmd in candidates:
            try:
                result = subprocess.run([cmd, "--version"], 
                                     capture_output=True, 
                                     timeout=5)
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        return "python"
    
    def _find_config(self) -> Optional[str]:
        """查找配置文件"""
        candidates = [
            MEMORY_SYSTEM_PATH / "config.yaml",
            Path.home() / ".memory" / "config.yaml",
            Path(os.environ.get("LOCALAPPDATA", "")) / ".memory" / "config.yaml",
        ]
        
        for p in candidates:
            if p.exists():
                return str(p)
        
        return None
    
    def _run_cli(self, *args) -> Dict[str, Any]:
        """运行 CLI 命令"""
        cmd = [self.python_path, self.cli_path]
        cmd.extend(args)
        
        env = os.environ.copy()
        if self.config_path:
            env['MEMORY_CONFIG'] = self.config_path
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30,
                env=env
            )
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except:
                    return {"status": "ok", "output": result.stdout}
            else:
                return {"status": "error", "message": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def store(
        self,
        content: str,
        memory_type: str = "general",
        tags: List[str] = None,
        importance: float = 5.0,
        visibility: str = "shared"
    ) -> Dict[str, Any]:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 类型 (general/project/preference/knowledge/team)
            tags: 标签列表
            importance: 重要性 1-10
            visibility: 可见性 (private/shared/global)
        
        Returns:
            结果字典
        """
        args = ["store", content, "--type", memory_type, "--importance", str(importance)]
        
        if tags:
            args.extend(["--tags", ",".join(tags)])
        
        if visibility != "shared":
            args.extend(["--visibility", visibility])
        
        return self._run_cli(*args)
    
    def search(
        self,
        query: str,
        memory_type: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        搜索记忆
        
        Args:
            query: 搜索内容
            memory_type: 类型过滤
            limit: 返回数量
        
        Returns:
            搜索结果
        """
        args = ["search", query, "--limit", str(limit)]
        
        if memory_type:
            args.extend(["--type", memory_type])
        
        return self._run_cli(*args)
    
    def list(
        self,
        memory_type: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        列出记忆
        """
        args = ["list", "--limit", str(limit)]
        
        if memory_type:
            args.extend(["--type", memory_type])
        
        return self._run_cli(*args)
    
    def get(self, memory_id: str) -> Dict[str, Any]:
        """
        获取单条记忆
        """
        return self._run_cli("get", memory_id)
    
    def delete(self, memory_id: str, hard: bool = False) -> Dict[str, Any]:
        """
        删除记忆
        """
        args = ["delete", memory_id]
        if hard:
            args.append("--hard")
        return self._run_cli(*args)
    
    def status(self) -> Dict[str, Any]:
        """
        查看状态
        """
        return self._run_cli("status")
    
    def tags(self) -> Dict[str, Any]:
        """
        列出所有标签
        """
        return self._run_cli("tags")
    
    def export(self, file_path: str = None) -> Dict[str, Any]:
        """
        导出记忆
        """
        args = ["export"]
        if file_path:
            args.extend(["--file", file_path])
        return self._run_cli(*args)
    
    def import_memories(self, file_path: str) -> Dict[str, Any]:
        """
        导入记忆
        """
        return self._run_cli("import", file_path)

    # ========== 经验分享核心功能 ==========

    def share_experience(
        self,
        tags: List[str] = None,
        min_importance: float = 6.0,
        memory_type: str = None,
        agent_name: str = None
    ) -> Dict[str, Any]:
        """
        分享经验到云端

        触发方式:
        - 用户说: "分享经验", "同步记忆", "sync"
        - 自动触发: 高重要性记忆 (importance >= 6)

        Args:
            tags: 只分享指定标签的记忆
            min_importance: 最低重要性阈值
            memory_type: 只分享指定类型
            agent_name: 显式指定来源代理名

        Returns:
            分享结果统计
        """
        args = ["share"]

        if tags:
            args.extend(["--tags", ",".join(tags)])

        args.extend(["--min-importance", str(min_importance)])

        if memory_type:
            args.extend(["--type", memory_type])

        if agent_name:
            args.extend(["--agent", agent_name])

        return self._run_cli(*args)

    def query_cloud_experience(
        self,
        query: str,
        tags: List[str] = None,
        memory_type: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        查询云端他人经验

        触发方式:
        - 用户说: "谁有xxx经验", "别人怎么做", "查一下云端"
        - 遇到问题时自动查询

        Args:
            query: 查询内容
            tags: 标签过滤
            memory_type: 类型过滤
            limit: 返回数量

        Returns:
            他人经验列表
        """
        args = ["cloud-query", query, "--limit", str(limit)]

        if tags:
            args.extend(["--tags", ",".join(tags)])

        if memory_type:
            args.extend(["--type", memory_type])

        return self._run_cli(*args)

    def sync(self, direction: str = "both") -> Dict[str, Any]:
        """
        双向同步云端记忆

        触发方式:
        - 用户说: "同步记忆", "sync memories"

        Args:
            direction: "push" / "pull" / "both"

        Returns:
            同步结果
        """
        args = ["sync", "--direction", direction]
        return self._run_cli(*args)

    def get_shared_memories(self, limit: int = 50) -> Dict[str, Any]:
        """
        获取所有共享记忆（来自所有代理）
        """
        args = ["list-shared", "--limit", str(limit)]
        return self._run_cli(*args)

    def get_my_experiences(self, limit: int = 50) -> Dict[str, Any]:
        """
        获取我分享过的经验
        """
        args = ["my-experiences", "--limit", str(limit)]
        return self._run_cli(*args)

    # ========== 触发器：分析用户消息 ==========

    SHARE_TRIGGERS = [
        r"分享.*经验",
        r"同步.*记忆",
        r"sync.*(?:memory|experience)",
        r"存到.*云端",
        r"上传.*经验",
    ]

    QUERY_CLOUD_TRIGGERS = [
        r"谁有.*经验",
        r"别人怎么",
        r"查一下.*云端",
        r"借鉴.*经验",
        r"参考.*做法",
        r"别人.*怎么做的",
        r"有没有.*经验",
    ]

    STORE_TRIGGERS = [
        r"记住",
        r"存到记忆",
        r"存储.*经验",
    ]

    def should_handle(self, message: str) -> Optional[Dict[str, Any]]:
        """
        分析用户消息，决定如何处理

        Args:
            message: 用户输入消息

        Returns:
            处理建议或 None
        """
        msg_lower = message.lower()

        # 检查是否要分享经验
        for pattern in self.SHARE_TRIGGERS:
            if re.search(pattern, msg_lower):
                return {
                    "action": "share_experience",
                    "message": message
                }

        # 检查是否要查询云端
        for pattern in self.QUERY_CLOUD_TRIGGERS:
            if re.search(pattern, msg_lower):
                return {
                    "action": "query_cloud",
                    "message": message
                }

        # 检查是否要存储记忆
        for pattern in self.STORE_TRIGGERS:
            if re.search(pattern, msg_lower):
                return {
                    "action": "store_memory",
                    "message": message
                }

        return None

    def handle(self, message: str) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            message: 用户输入消息

        Returns:
            处理结果
        """
        decision = self.should_handle(message)

        if decision is None:
            return {
                "status": "no_action",
                "message": message
            }

        action = decision["action"]

        if action == "share_experience":
            return self.share_experience()

        elif action == "query_cloud":
            # 提取查询内容
            query = self._extract_query(message)
            return self.query_cloud_experience(query)

        elif action == "store_memory":
            # 提取要存储的内容
            content = self._extract_content(message)
            if content:
                return self.store(content, tags=["用户指示"])
            return {"status": "error", "message": "未能提取记忆内容"}

        return {"status": "unknown_action"}

    def _extract_query(self, message: str) -> str:
        """从消息中提取查询内容"""
        # 移除触发词，保留查询内容
        patterns = [
            r"谁有.*经验[？?]?",
            r"别人怎么.*[？?]?",
            r"查一下.*云端[？?]?",
            r"借鉴.*经验[？?]?",
            r"参考.*做法[？?]?",
            r"有没有.*经验[？?]?",
        ]

        query = message
        for pattern in patterns:
            query = re.sub(pattern, "", query)

        return query.strip() or message

    def _extract_content(self, message: str) -> Optional[str]:
        """从消息中提取要存储的内容"""
        # 尝试提取引号内的内容
        match = re.search(r'[""''](.+?)["""]', message)
        if match:
            return match.group(1)

        # 移除"记住"等触发词
        patterns = [r"记住[，,]?", r"存到记忆[，,]?", r"存储.*经验[，,]?"]
        content = message
        for pattern in patterns:
            content = re.sub(pattern, "", content)

        return content.strip() or None


# 全局实例
_memory_skill: Optional[MemorySkill] = None


def get_memory_skill() -> MemorySkill:
    """获取全局 MemorySkill 实例"""
    global _memory_skill
    if _memory_skill is None:
        _memory_skill = MemorySkill()
    return _memory_skill


# 便捷函数
def store(content: str, **kwargs) -> Dict[str, Any]:
    """存储记忆"""
    return get_memory_skill().store(content, **kwargs)


def search(query: str, **kwargs) -> Dict[str, Any]:
    """搜索记忆"""
    return get_memory_skill().search(query, **kwargs)


def list_memories(**kwargs) -> Dict[str, Any]:
    """列出记忆"""
    return get_memory_skill().list(**kwargs)


def status() -> Dict[str, Any]:
    """查看状态"""
    return get_memory_skill().status()


def share_experience(**kwargs) -> Dict[str, Any]:
    """分享经验到云端"""
    return get_memory_skill().share_experience(**kwargs)


def query_cloud_experience(query: str, **kwargs) -> Dict[str, Any]:
    """查询云端他人经验"""
    return get_memory_skill().query_cloud_experience(query, **kwargs)


def sync(**kwargs) -> Dict[str, Any]:
    """双向同步"""
    return get_memory_skill().sync(**kwargs)


def handle_message(message: str) -> Dict[str, Any]:
    """处理用户消息，自动判断动作"""
    return get_memory_skill().handle(message)


# 测试
if __name__ == "__main__":
    skill = MemorySkill()
    print("Testing MemorySkill...")
    
    # Status
    print("\n1. Status:")
    result = skill.status()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Store
    print("\n2. Store:")
    result = skill.store(
        content="这是一条测试记忆",
        memory_type="project",
        tags=["test", "example"]
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Search
    print("\n3. Search:")
    result = skill.search("测试")
    print(json.dumps(result, indent=2, ensure_ascii=False))
