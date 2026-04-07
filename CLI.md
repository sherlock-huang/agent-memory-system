# Memory Sharing CLI
## Agent 快速记忆共享命令行工具

**版本:** v1.0  
**日期:** 2026-04-07  
**设计原则:** CLI-first, zero-friction, agent-native

---

## 1. 设计理念

### Agent 使用场景

```
Claude Code / Codex / OpenClaw
         │
         │  exec("memory search 'python 编码规范'")
         │  exec("memory store '项目用 pytest'" --type project)
         │
         ↓
   Memory CLI
         │
         ├── 本地 SQLite (< 1ms 延迟)
         ├── HTTP API (可选，用于跨机器)
         └── 输出 JSON (便于解析)
```

### 设计原则

| 原则 | 说明 |
|------|------|
| **即时可用** | `memory` 命令行工具，下载即用，无需配置 |
| **管道友好** | 输出 JSON，支持 `jq` / `grep` / `awk` |
| **最小参数** | 默认值优先，减少每次输入 |
| **本地优先** | SQLite 本地存储，零网络延迟 |
| **静默失败** | 错误输出到 stderr，不污染 stdout |

---

## 2. 命令设计

### 2.1 核心命令

```bash
# 存储记忆 (最常用)
memory store "内容..." [--type project] [--tags py,fastapi] [--importance 8]

# 搜索记忆 (最常用)
memory search "查询内容" [--limit 10] [--type project]

# 获取记忆
memory get <id>

# 列出记忆
memory list [--type project] [--limit 20]

# 删除记忆
memory delete <id> [--hard]

# 分享记忆
memory share <id> [--to agent-id] [--visibility shared]

# 查看状态
memory status

# 帮助
memory help
```

### 2.2 命令示例

```bash
# 存储一个项目偏好
memory store "这个项目使用 Python FastAPI，偏好类型注解" \
  --type project \
  --tags python,fastapi,typing \
  --importance 8 \
  --project /path/to/project

# 搜索项目相关记忆
memory search "python 编码规范" --type project --limit 5

# 快速存储（最小语法）
memory s "用 pytest 测试"

# 快速搜索（最小语法）
memory s "fastapi"

# 存储用户偏好
memory store "用户喜欢简洁的回复，不要太多废话" \
  --type preference \
  --tags communication,style

# 列出所有项目记忆
memory list --type project

# 删除记忆
memory delete shr_abc123

# 永久删除
memory delete shr_abc123 --hard

# 导出记忆（用于备份）
memory export --format json > memories.json

# 导入记忆
memory import memories.json
```

---

## 3. 实现架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         memory CLI                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CLI Layer (Typer/Click)                                        │
│  ├── memory store <content>                                     │
│  ├── memory search <query>                                      │
│  ├── memory get <id>                                            │
│  ├── memory list                                                │
│  ├── memory delete <id>                                        │
│  └── memory status                                             │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Core Engine                             │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │ StoreEngine  │  │ SearchEngine │  │ ACLEngine   │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Storage Layer                              │   │
│  │                                                           │   │
│  │  ┌─────────────────┐    ┌─────────────────┐              │   │
│  │  │  SQLite         │    │  File Cache     │              │   │
│  │  │  (shared_mem)   │    │  (.memory/)     │              │   │
│  │  └─────────────────┘    └─────────────────┘              │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
~/.memory/                              # 工作目录
├── config.yaml                         # 配置文件
├── memory.db                           # SQLite 数据库
├── .cache/                            # 缓存
│   ├── embeddings/                    # 嵌入向量缓存
│   └── search_history.json            # 搜索历史
├── logs/                              # 日志
│   └── memory.log
└── backup/                            # 备份
    └── 2026-04-07.json
```

### 3.3 数据库 Schema (简化版)

```sql
-- 共享记忆表
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    summary TEXT,
    
    -- 分类
    type TEXT NOT NULL DEFAULT 'general',  -- general | project | preference | knowledge
    visibility TEXT NOT NULL DEFAULT 'shared',  -- private | shared | global
    
    -- 来源
    source TEXT NOT NULL,                  -- 'openclaw' | 'claude_code' | 'codex'
    source_agent TEXT,                     -- Agent ID
    project_path TEXT,                     -- 关联项目
    
    -- 评分
    importance REAL DEFAULT 5.0,
    
    -- 标签
    tags TEXT,                             -- JSON: '["python", "fastapi"]'
    
    -- 时间
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    -- 状态
    is_deleted INTEGER DEFAULT 0
);

-- 向量缓存表
CREATE TABLE embeddings (
    content_hash TEXT PRIMARY KEY,         -- SHA256(content)
    embedding BLOB,                        -- 二进制向量
    model TEXT,                            -- 嵌入模型
    created_at INTEGER
);

-- 索引
CREATE INDEX idx_memories_type ON memories(type);
CREATE INDEX idx_memories_visibility ON memories(visibility);
CREATE INDEX idx_memories_project ON memories(project_path);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
```

---

## 4. CLI 实现

### 4.1 主程序 (Python)

```python
#!/usr/bin/env python3
# memory_cli.py
"""
Memory Sharing CLI - Agent 快速记忆工具
用法: memory <command> [args]
"""

import sys
import json
import argparse
from typing import Optional, List
from datetime import datetime

# 内部模块
from core.database import Database
from core.search import SearchEngine
from core.config import Config


class MemoryCLI:
    """记忆 CLI 主类"""
    
    def __init__(self):
        self.db = Database()
        self.search = SearchEngine(self.db)
        self.config = Config()
    
    def store(self, content: str, **kwargs) -> dict:
        """存储记忆"""
        memory = self.db.insert(
            content=content,
            type=kwargs.get('type', 'general'),
            visibility=kwargs.get('visibility', 'shared'),
            tags=kwargs.get('tags', []),
            importance=kwargs.get('importance', 5.0),
            project_path=kwargs.get('project'),
            source=kwargs.get('source', 'cli'),
            source_agent=kwargs.get('agent_id'),
        )
        
        return {
            "status": "stored",
            "id": memory['id'],
            "type": memory['type'],
            "created_at": memory['created_at']
        }
    
    def search(self, query: str, **kwargs) -> dict:
        """搜索记忆"""
        results = self.search.query(
            query=query,
            limit=kwargs.get('limit', 10),
            memory_type=kwargs.get('type'),
            project_path=kwargs.get('project'),
        )
        
        return {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": results
        }
    
    def get(self, memory_id: str) -> dict:
        """获取单条记忆"""
        memory = self.db.get(memory_id)
        
        if not memory:
            return {"status": "error", "message": "Memory not found"}
        
        return {
            "status": "ok",
            "memory": memory
        }
    
    def list(self, **kwargs) -> dict:
        """列出记忆"""
        memories = self.db.list(
            memory_type=kwargs.get('type'),
            project_path=kwargs.get('project'),
            limit=kwargs.get('limit', 50),
            offset=kwargs.get('offset', 0)
        )
        
        total = self.db.count(kwargs.get('type'), kwargs.get('project'))
        
        return {
            "status": "ok",
            "total": total,
            "count": len(memories),
            "memories": memories
        }
    
    def delete(self, memory_id: str, hard: bool = False) -> dict:
        """删除记忆"""
        success = self.db.delete(memory_id, hard=hard)
        
        return {
            "status": "deleted" if success else "error",
            "id": memory_id
        }
    
    def status(self) -> dict:
        """状态"""
        stats = self.db.stats()
        
        return {
            "status": "ok",
            "version": "1.0.0",
            "db_path": self.db.path,
            "stats": stats
        }


def main():
    parser = argparse.ArgumentParser(
        prog='memory',
        description='Memory Sharing CLI - Agent 快速记忆工具'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # store 命令
    store_parser = subparsers.add_parser('store', aliases=['s', 'add'])
    store_parser.add_argument('content', help='记忆内容')
    store_parser.add_argument('--type', '-t', default='general', 
                              choices=['general', 'project', 'preference', 'knowledge'],
                              help='记忆类型')
    store_parser.add_argument('--tags', '-g', default='',
                              help='标签，逗号分隔')
    store_parser.add_argument('--importance', '-i', type=float, default=5.0,
                              help='重要性 1-10')
    store_parser.add_argument('--project', '-p', default=None,
                              help='项目路径')
    
    # search 命令
    search_parser = subparsers.add_parser('search', aliases=['s', 'find'])
    search_parser.add_argument('query', help='搜索内容')
    search_parser.add_argument('--limit', '-l', type=int, default=10,
                              help='返回数量')
    search_parser.add_argument('--type', '-t', default=None,
                              help='记忆类型')
    search_parser.add_argument('--project', '-p', default=None,
                              help='项目路径')
    
    # get 命令
    get_parser = subparsers.add_parser('get', aliases=['g'])
    get_parser.add_argument('id', help='记忆 ID')
    
    # list 命令
    list_parser = subparsers.add_parser('list', aliases=['ls', 'l'])
    list_parser.add_argument('--type', '-t', default=None)
    list_parser.add_argument('--project', '-p', default=None)
    list_parser.add_argument('--limit', '-l', type=int, default=50)
    list_parser.add_argument('--offset', '-o', type=int, default=0)
    
    # delete 命令
    delete_parser = subparsers.add_parser('delete', aliases=['rm', 'd'])
    delete_parser.add_argument('id', help='记忆 ID')
    delete_parser.add_argument('--hard', action='store_true',
                              help='永久删除')
    
    # status 命令
    status_parser = subparsers.add_parser('status', aliases=['stat', 'st'])
    
    # help 命令
    help_parser = subparsers.add_parser('help')
    
    args = parser.parse_args()
    
    # 无命令时显示 help
    if not args.command:
        parser.print_help()
        return
    
    cli = MemoryCLI()
    
    # 执行命令
    try:
        if args.command in ['store', 's', 'add']:
            tags = args.tags.split(',') if args.tags else []
            result = cli.store(
                content=args.content,
                type=args.type,
                tags=tags,
                importance=args.importance,
                project=args.project,
                source='cli'
            )
            
        elif args.command in ['search', 's', 'find']:
            result = cli.search(
                query=args.query,
                limit=args.limit,
                memory_type=args.type,
                project_path=args.project
            )
            
        elif args.command in ['get', 'g']:
            result = cli.get(args.id)
            
        elif args.command in ['list', 'ls', 'l']:
            result = cli.list(
                memory_type=args.type,
                project_path=args.project,
                limit=args.limit,
                offset=args.offset
            )
            
        elif args.command in ['delete', 'rm', 'd']:
            result = cli.delete(args.id, hard=args.hard)
            
        elif args.command in ['status', 'stat', 'st']:
            result = cli.status()
            
        else:
            parser.print_help()
            return
        
        # 输出 JSON 到 stdout
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        # 错误输出到 stderr
        import sys
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

### 4.2 核心数据库模块

```python
# core/database.py
"""
SQLite 数据库管理 - 简化版
"""

import sqlite3
import json
import uuid
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class Memory:
    id: str
    content: str
    type: str
    visibility: str
    importance: float
    tags: List[str]
    created_at: int


class Database:
    """SQLite 数据库"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / '.memory' / 'memory.db'
        
        self.path = str(db_path)
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                summary TEXT,
                type TEXT NOT NULL DEFAULT 'general',
                visibility TEXT NOT NULL DEFAULT 'shared',
                source TEXT NOT NULL DEFAULT 'cli',
                source_agent TEXT,
                project_path TEXT,
                importance REAL DEFAULT 5.0,
                tags TEXT DEFAULT '[]',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                is_deleted INTEGER DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_memories_visibility ON memories(visibility);
            CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_path);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
            
            CREATE TABLE IF NOT EXISTS embeddings (
                content_hash TEXT PRIMARY KEY,
                embedding BLOB,
                model TEXT,
                created_at INTEGER
            );
        """)
        self._conn.commit()
    
    def insert(self, content: str, **kwargs) -> Dict:
        """插入记忆"""
        now = int(time.time() * 1000)
        mem_id = f"mem_{uuid.uuid4().hex[:10]}"
        
        tags = kwargs.get('tags', [])
        if isinstance(tags, list):
            tags = json.dumps(tags, ensure_ascii=False)
        
        self._conn.execute("""
            INSERT INTO memories (
                id, content, summary, type, visibility,
                source, source_agent, project_path, importance,
                tags, created_at, updated_at, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            mem_id,
            content,
            kwargs.get('summary'),
            kwargs.get('type', 'general'),
            kwargs.get('visibility', 'shared'),
            kwargs.get('source', 'cli'),
            kwargs.get('source_agent'),
            kwargs.get('project_path'),
            kwargs.get('importance', 5.0),
            tags,
            now,
            now
        ))
        self._conn.commit()
        
        return self.get(mem_id)
    
    def get(self, memory_id: str) -> Optional[Dict]:
        """获取单条记忆"""
        cursor = self._conn.execute(
            "SELECT * FROM memories WHERE id = ? AND is_deleted = 0",
            (memory_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_dict(row)
    
    def list(self, memory_type: str = None, project_path: str = None,
             limit: int = 50, offset: int = 0) -> List[Dict]:
        """列出记忆"""
        conditions = ["is_deleted = 0"]
        params = []
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        where = " AND ".join(conditions)
        
        cursor = self._conn.execute(f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (*params, limit, offset))
        
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def search(self, query: str, memory_type: str = None,
               project_path: str = None, limit: int = 10) -> List[Dict]:
        """简单搜索 (LIKE)"""
        conditions = ["is_deleted = 0"]
        params = []
        
        # 简单关键词匹配
        conditions.append("(content LIKE ? OR tags LIKE ?)")
        pattern = f"%{query}%"
        params.extend([pattern, pattern])
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        where = " AND ".join(conditions)
        
        cursor = self._conn.execute(f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """, (*params, limit))
        
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def delete(self, memory_id: str, hard: bool = False) -> bool:
        """删除记忆"""
        if hard:
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        else:
            self._conn.execute(
                "UPDATE memories SET is_deleted = 1, updated_at = ? WHERE id = ?",
                (int(time.time() * 1000), memory_id)
            )
        self._conn.commit()
        return True
    
    def count(self, memory_type: str = None, project_path: str = None) -> int:
        """统计数量"""
        conditions = ["is_deleted = 0"]
        params = []
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)
        
        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)
        
        where = " AND ".join(conditions)
        
        cursor = self._conn.execute(
            f"SELECT COUNT(*) as c FROM memories WHERE {where}",
            tuple(params)
        )
        return cursor.fetchone()['c']
    
    def stats(self) -> Dict:
        """统计信息"""
        cursor = self._conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN type = 'project' THEN 1 ELSE 0 END) as projects,
                SUM(CASE WHEN type = 'preference' THEN 1 ELSE 0 END) as preferences,
                SUM(CASE WHEN type = 'knowledge' THEN 1 ELSE 0 END) as knowledge
            FROM memories WHERE is_deleted = 0
        """)
        row = cursor.fetchone()
        
        return dict(row)
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Row 转 Dict"""
        d = dict(row)
        # 解析 tags
        if 'tags' in d and d['tags']:
            try:
                d['tags'] = json.loads(d['tags'])
            except:
                d['tags'] = []
        return d
    
    def close(self):
        """关闭连接"""
        self._conn.close()
```

### 4.3 搜索模块

```python
# core/search.py
"""
搜索引擎 - 支持向量 + 关键词混合搜索
"""

import json
import hashlib
from typing import List, Dict, Optional
from .database import Database


class SearchEngine:
    """记忆搜索引擎"""
    
    def __init__(self, db: Database):
        self.db = db
        
        # 简单嵌入实现 (可用 OpenAI/Ollama 替换)
        self._embedding_cache = {}
    
    def query(self, query: str, limit: int = 10,
              memory_type: str = None,
              project_path: str = None) -> List[Dict]:
        """
        查询记忆
        策略:
        1. 精确匹配优先
        2. 关键词匹配
        3. 相关性排序
        """
        # 简单实现: 关键词搜索 + 重要性排序
        results = self.db.search(
            query=query,
            memory_type=memory_type,
            project_path=project_path,
            limit=limit * 2  # 多取一些，后面过滤
        )
        
        # 计算相关性分数
        scored = []
        query_lower = query.lower()
        
        for r in results:
            score = 0.0
            
            # 精确包含加分
            if query_lower in r['content'].lower():
                score += 0.5
            
            # 标签匹配加分
            tags = r.get('tags', [])
            for tag in tags:
                if query_lower in tag.lower():
                    score += 0.3
            
            # 重要性加权
            score += r['importance'] / 10.0 * 0.2
            
            r['score'] = round(score, 3)
            scored.append(r)
        
        # 排序
        scored.sort(key=lambda x: (x['score'], x['importance']), reverse=True)
        
        return scored[:limit]
    
    def embed(self, text: str) -> Optional[List[float]]:
        """
        生成文本向量
        简化实现: 返回伪向量
        生产环境应调用 OpenAI/Ollama API
        """
        # 检查缓存
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # 尝试从数据库加载
        cursor = self.db._conn.execute(
            "SELECT embedding FROM embeddings WHERE content_hash = ?",
            (content_hash,)
        )
        row = cursor.fetchone()
        
        if row and row['embedding']:
            import struct
            return list(struct.unpack('1536f', row['embedding']))
        
        # 简化: 返回文本的简单哈希作为伪向量 (用于演示)
        # 生产环境应调用真实的嵌入 API
        pseudo_vector = [float(ord(c) % 100) / 100 for c in text[:1536]]
        # 补齐到 1536 维
        while len(pseudo_vector) < 1536:
            pseudo_vector.append(0.0)
        
        return pseudo_vector[:1536]
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)
```

---

## 5. Agent 集成方式

### 5.1 OpenClaw 集成

在 OpenClaw 的 skill 或 system prompt 中添加：

```markdown
## Memory Commands
你可以通过以下命令访问共享记忆:

- `memory store <content>` - 存储重要信息
- `memory search <query>` - 搜索相关记忆  
- `memory list --type project` - 列出项目记忆
- `memory get <id>` - 获取记忆详情

规则:
1. 开始新任务前，先搜索相关记忆
2. 重要决策完成后，存储到共享记忆
3. 使用 --type project 标记项目相关信息
4. 使用 --tags 添加标签，便于后续检索
```

### 5.2 Claude Code / Codex 集成

创建 `.claude/commands/memory.md` 或 `~/.codex/memory.py`:

```bash
#!/bin/bash
# memory - 快速记忆命令

MEMORY_CLI="/path/to/memory_cli.py"
COMMAND="$1"
shift

python3 "$MEMORY_CLI" "$COMMAND" "$@"
```

使用时：

```bash
# Claude Code / Codex 中
exec("memory store '这个模块使用策略模式' --type project --tags design-pattern")

exec("memory search '策略模式' --type project")
```

### 5.3 Python SDK 封装

```python
# memory_sdk.py
"""
Python SDK - 一行代码存储和检索记忆
"""

import subprocess
import json
from typing import List, Optional, Dict


class Memory:
    """记忆 SDK"""
    
    def __init__(self, cli_path: str = None):
        self.cli = cli_path or self._find_cli()
    
    def _find_cli(self) -> str:
        """查找 memory CLI"""
        import shutil
        path = shutil.which('memory')
        if path:
            return path
        # 尝试常见位置
        import os
        home = os.path.expanduser('~')
        for path in [
            f'{home}/.local/bin/memory',
            f'{home}/.memory/memory_cli.py'
        ]:
            if os.path.exists(path):
                return path
        raise FileNotFoundError("memory CLI not found")
    
    def _run(self, *args) -> dict:
        """运行 CLI 命令"""
        result = subprocess.run(
            [self.cli] + list(args),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        
        return json.loads(result.stdout)
    
    def store(self, content: str, **kwargs) -> str:
        """
        存储记忆
        
        用法:
        memory.store("内容", type="project", tags=["python"])
        """
        args = ['store', content]
        
        if kwargs.get('type'):
            args.extend(['--type', kwargs['type']])
        if kwargs.get('tags'):
            args.extend(['--tags', ','.join(kwargs['tags'])])
        if kwargs.get('importance'):
            args.extend(['--importance', str(kwargs['importance'])])
        if kwargs.get('project'):
            args.extend(['--project', kwargs['project']])
        
        result = self._run(*args)
        return result['id']
    
    def search(self, query: str, **kwargs) -> List[Dict]:
        """
        搜索记忆
        
        用法:
        results = memory.search("python 规范")
        for r in results:
            print(r['content'])
        """
        args = ['search', query]
        
        if kwargs.get('limit'):
            args.extend(['--limit', str(kwargs['limit'])])
        if kwargs.get('type'):
            args.extend(['--type', kwargs['type']])
        if kwargs.get('project'):
            args.extend(['--project', kwargs['project']])
        
        result = self._run(*args)
        return result['results']
    
    def get(self, memory_id: str) -> Dict:
        """获取记忆详情"""
        result = self._run('get', memory_id)
        return result['memory']
    
    def list(self, **kwargs) -> List[Dict]:
        """列出记忆"""
        args = ['list']
        
        if kwargs.get('type'):
            args.extend(['--type', kwargs['type']])
        if kwargs.get('limit'):
            args.extend(['--limit', str(kwargs['limit'])])
        
        result = self._run(*args)
        return result['memories']
    
    def delete(self, memory_id: str, hard: bool = False):
        """删除记忆"""
        args = ['delete', memory_id]
        if hard:
            args.append('--hard')
        self._run(*args)


# 全局实例
memory = Memory()

# 使用示例
if __name__ == '__main__':
    # 存储
    mem_id = memory.store(
        "项目使用 FastAPI 框架",
        type="project",
        tags=["python", "fastapi"]
    )
    print(f"Stored: {mem_id}")
    
    # 搜索
    results = memory.search("python")
    for r in results:
        print(f"- {r['content']} (score: {r.get('score', 0)})")
```

---

## 6. 安装与配置

### 6.1 快速安装

```bash
# 下载 CLI
curl -fsSL https://example.com/memory_cli.py -o ~/.local/bin/memory
chmod +x ~/.local/bin/memory

# 或通过 pip
pip install memory-cli

# 验证
memory status
```

### 6.2 配置文件

```yaml
# ~/.memory/config.yaml

# 数据库
db_path: ~/.memory/memory.db

# 搜索
search:
  default_limit: 10
  max_limit: 100

# 嵌入 (可选)
embedding:
  provider: local  # local | openai | ollama
  model: nomic-embed-text

# 源标识
source: cli
agent_id: ${AGENT_ID:-cli}
```

---

## 7. 输出格式

### 7.1 JSON 输出 (默认)

```bash
$ memory search "python"

{
  "status": "ok",
  "query": "python",
  "count": 2,
  "results": [
    {
      "id": "mem_a1b2c3d4",
      "content": "项目使用 Python FastAPI",
      "type": "project",
      "importance": 8.0,
      "tags": ["python", "fastapi"],
      "score": 0.85,
      "created_at": 1712467200000
    }
  ]
}
```

### 7.2 简洁输出 (--quiet)

```bash
$ memory search "python" --quiet

mem_a1b2c3d4  项目使用 Python FastAPI
mem_e5f6g7h8  用户偏好 Python 而不是 JavaScript
```

### 7.3 错误输出

```bash
$ memory get invalid_id

# stderr:
{"status": "error", "message": "Memory not found"}

# exit code: 1
```

---

## 8. 性能目标

| 操作 | 目标延迟 | 说明 |
|------|----------|------|
| `memory store` | < 50ms | 写入 + 索引 |
| `memory search` | < 100ms | 10条结果 |
| `memory list` | < 50ms | 50条 |
| `memory status` | < 10ms | 统计查询 |

---

## 9. 扩展计划

- [ ] 向量搜索支持 (sqlite-vec)
- [ ] OpenAI/Ollama 嵌入集成
- [ ] 全文搜索 (FTS5)
- [ ] HTTP API 服务模式
- [ ] 多用户/多 Agent 支持
- [ ] 备份与恢复
- [ ] Web UI

---

*CLI-first Memory System v1.0*
