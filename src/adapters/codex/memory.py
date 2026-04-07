#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Module for Codex
Codex 可以直接 import 这个模块来使用记忆功能

用法:
    from memory import memory
    memory.store("内容", type="project")
    results = memory.search("查询")
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

# 配置
MEMORY_SYSTEM_PATH = Path(__file__).parent.parent.parent  # agent-memory-system
CLI_PATH = MEMORY_SYSTEM_PATH / "src" / "cli" / "memory_cli.py"

# Python 解释器
PYTHON_CMD = os.environ.get("PYTHON", "python")


class MemoryClient:
    """
    Memory Client for Codex
    提供简单的 Python API 访问共享记忆
    """
    
    def __init__(self):
        self.cli_path = str(CLI_PATH)
        self.python_cmd = PYTHON_CMD
    
    def _run(self, *args) -> Dict[str, Any]:
        """执行 CLI 命令"""
        cmd = [self.python_cmd, self.cli_path] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
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
        type: str = "general",
        tags: List[str] = None,
        importance: float = 5.0,
        visibility: str = "shared"
    ) -> str:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            type: 类型 (general/project/preference/knowledge/team)
            tags: 标签列表
            importance: 重要性 1-10
            visibility: 可见性
        
        Returns:
            记忆 ID
        """
        args = ["store", content, "--type", type, "--importance", str(importance)]
        
        if tags:
            args.extend(["--tags", ",".join(tags)])
        
        if visibility != "shared":
            args.extend(["--visibility", visibility])
        
        result = self._run(*args)
        
        if result.get("status") == "stored":
            return result.get("id", "")
        
        raise RuntimeError(result.get("message", "Failed to store memory"))
    
    def search(
        self,
        query: str,
        type: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索内容
            type: 类型过滤
            limit: 返回数量
        
        Returns:
            记忆列表
        """
        args = ["search", query, "--limit", str(limit)]
        
        if type:
            args.extend(["--type", type])
        
        result = self._run(*args)
        
        return result.get("results", [])
    
    def get(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆详情"""
        result = self._run("get", memory_id)
        return result.get("memory", {})
    
    def list(
        self,
        type: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """列出记忆"""
        args = ["list", "--limit", str(limit)]
        
        if type:
            args.extend(["--type", type])
        
        result = self._run(*args)
        return result.get("memories", [])
    
    def delete(self, memory_id: str, hard: bool = False):
        """删除记忆"""
        args = ["delete", memory_id]
        if hard:
            args.append("--hard")
        
        return self._run(*args)
    
    def status(self) -> Dict[str, Any]:
        """查看状态"""
        return self._run("status")
    
    def tags(self) -> List[Dict[str, Any]]:
        """列出标签"""
        result = self._run("tags")
        return result.get("tags", [])
    
    def export(self) -> Dict[str, Any]:
        """导出所有记忆"""
        return self._run("export")
    
    def import_memories(self, file_path: str) -> int:
        """导入记忆"""
        result = self._run("import", file_path)
        return result.get("imported", 0)


# 全局实例
memory = MemoryClient()


# 便捷函数
def store(content: str, **kwargs) -> str:
    """存储记忆"""
    return memory.store(content, **kwargs)


def search(query: str, **kwargs) -> List[Dict[str, Any]]:
    """搜索记忆"""
    return memory.search(query, **kwargs)


def list_all(**kwargs) -> List[Dict[str, Any]]:
    """列出记忆"""
    return memory.list(**kwargs)


# 测试
if __name__ == "__main__":
    print("Memory Client for Codex")
    print("=" * 40)
    
    # Status
    print("\n1. Status:")
    status = memory.status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # Store
    print("\n2. Store:")
    mem_id = memory.store(
        "Codex 测试记忆",
        type="project",
        tags=["test", "codex"]
    )
    print(f"Stored: {mem_id}")
    
    # Search
    print("\n3. Search:")
    results = memory.search("测试")
    print(f"Found: {len(results)} results")
