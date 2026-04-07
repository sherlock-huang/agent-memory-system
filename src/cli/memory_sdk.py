#!/usr/bin/env python3
"""
Memory SDK - Python 封装
让 Agent 可以直接 import memory 使用

用法:
    from memory_sdk import memory
    memory.store("内容", type="project")
    results = memory.search("查询")
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional


class MemorySDK:
    """
    Memory SDK - 一行代码存储和检索记忆
    
    示例:
        from memory_sdk import memory
        memory.store("内容", type="project")
        results = memory.search("查询")
    """
    
    def __init__(self, cli_path: str = None):
        self._cli_path = cli_path or self._find_cli()
    
    def _find_cli(self) -> Optional[str]:
        """查找 memory CLI"""
        import os
        
        # 1. 检查环境变量
        env_path = os.environ.get('MEMORY_CLI')
        if env_path and Path(env_path).exists():
            return env_path
        
        # 2. 检查常见位置
        home = Path.home()
        candidates = [
            home / '.local' / 'bin' / 'memory',
            home / '.local' / 'bin' / 'memory.py',
            home / '.memory' / 'memory_cli.py',
            home / 'bin' / 'memory',
            Path(sys.executable).parent / 'memory.py',
        ]
        
        # 3. 检查 PATH 中的 memory
        for path in Path('/usr/local/bin').glob('memory*'):
            return str(path)
        for path in Path(home / '.local' / 'bin').glob('memory*'):
            return str(path)
        
        return None
    
    def _run(self, *args) -> dict:
        """运行 CLI 命令"""
        if not self._cli_path:
            raise RuntimeError(
                "memory CLI not found. "
                "Please install: curl -fsSL .../memory_cli.py -o ~/.local/bin/memory"
            )
        
        result = subprocess.run(
            [sys.executable, self._cli_path] + list(args),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        
        return json.loads(result.stdout)
    
    def store(
        self,
        content: str,
        type: str = "general",
        tags: List[str] = None,
        importance: float = 5.0,
        project: str = None
    ) -> str:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            type: 类型 (general, project, preference, knowledge)
            tags: 标签列表
            importance: 重要性 1-10
            project: 项目路径
        
        Returns:
            记忆 ID
        
        Example:
            memory.store("项目使用 FastAPI", type="project", tags=["python"])
        """
        args = ['store', content, '--type', type, '--importance', str(importance)]
        
        if tags:
            args.extend(['--tags', ','.join(tags)])
        if project:
            args.extend(['--project', project])
        
        result = self._run(*args)
        return result['id']
    
    def search(
        self,
        query: str,
        limit: int = 10,
        type: str = None,
        project: str = None
    ) -> List[Dict]:
        """
        搜索记忆
        
        Args:
            query: 搜索内容
            limit: 返回数量
            type: 记忆类型过滤
            project: 项目路径
        
        Returns:
            记忆列表
        
        Example:
            results = memory.search("python")
            for r in results:
                print(f"{r['id']}: {r['content']}")
        """
        args = ['search', query, '--limit', str(limit)]
        
        if type:
            args.extend(['--type', type])
        if project:
            args.extend(['--project', project])
        
        result = self._run(*args)
        return result['results']
    
    def get(self, memory_id: str) -> Dict:
        """
        获取记忆详情
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            记忆详情字典
        """
        result = self._run('get', memory_id)
        return result.get('memory', {})
    
    def list(
        self,
        type: str = None,
        project: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        列出记忆
        
        Args:
            type: 记忆类型过滤
            project: 项目路径
            limit: 返回数量
            offset: 跳过数量
        
        Returns:
            记忆列表
        """
        args = ['list', '--limit', str(limit), '--offset', str(offset)]
        
        if type:
            args.extend(['--type', type])
        if project:
            args.extend(['--project', project])
        
        result = self._run(*args)
        return result.get('memories', [])
    
    def delete(self, memory_id: str, hard: bool = False):
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            hard: 是否永久删除
        """
        args = ['delete', memory_id]
        if hard:
            args.append('--hard')
        self._run(*args)
    
    def status(self) -> Dict:
        """
        获取状态统计
        
        Returns:
            状态字典
        """
        return self._run('status')
    
    def export(self) -> Dict:
        """
        导出所有记忆
        
        Returns:
            导出数据
        """
        return self._run('export')


# 全局单例
memory = MemorySDK()

# 方便导入使用
__all__ = ['MemorySDK', 'memory']
