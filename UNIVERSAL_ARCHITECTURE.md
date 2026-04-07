# Agent Universal Memory Architecture
## 统一记忆架构设计方案（修订版）

**目标 Agent:** OpenClaw, Claude Code (Codex), Codex  
**日期:** 2026-04-07  
**版本:** v2.0  
**定位:** 以 OpenClaw 官方记忆系统为**核心**，跨 Agent 共享层为**补充**

---

## 📋 目录

1. [架构定位](#架构定位)
2. [OpenClaw 官方记忆系统分析](#openclaw-官方记忆系统分析)
3. [跨 Agent 记忆共享层设计](#跨-agent-记忆共享层设计)
4. [Claude Code / Codex 集成方案](#claude-code--codex-集成方案)
5. [实施路线图](#实施路线图)
6. [与官方系统的分工](#与官方系统的分工)

---

## 架构定位

### 核心策略

```
┌─────────────────────────────────────────────────────────────────┐
│                    修订后的架构定位                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │           OpenClaw 官方记忆系统 (内置, 已完善)              │  │
│   │                                                          │  │
│   │  MEMORY.md + memory/*.md → Dreaming → SQLite+向量索引     │  │
│   │                                                          │  │
│   │  ✅ 三阶段巩固 (Light/Deep/REM)                          │  │
│   │  ✅ 混合检索 (BM25 + 向量)                               │  │
│   │  ✅ Dreams UI                                            │  │
│   │  ✅ 自动 cron 调度                                       │  │
│   │  ✅ 本地 SQLite，无额外依赖                               │  │
│   └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │           跨 Agent 共享层 (新增)                          │  │
│   │                                                          │  │
│   │  目标: 让 Claude Code / Codex 也能使用 OpenClaw 的记忆    │  │
│   │                                                          │  │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │  │
│   │  │  OpenClaw  │  │Claude Code│  │   Codex    │       │  │
│   │  │  (原生)    │  │ (适配器)  │  │  (适配器)  │       │  │
│   │  └────────────┘  └────────────┘  └────────────┘       │  │
│   │          ↓               ↓               ↓              │  │
│   │  ┌──────────────────────────────────────────────┐     │  │
│   │  │         Memory Sharing Gateway API            │     │  │
│   │  │  (读写 OpenClaw SQLite 索引，对外提供 REST)   │     │  │
│   │  └──────────────────────────────────────────────┘     │  │
│   │                              ↓                         │  │
│   │  ┌──────────────────────────────────────────────┐     │  │
│   │  │         Shared Memory Layer                  │     │  │
│   │  │   - 项目共享记忆 (shared)                    │     │  │
│   │  │   - 跨 Agent 知识 (global)                   │     │  │
│   │  │   - 访问控制 (ACL)                           │     │  │
│   │  └──────────────────────────────────────────────┘     │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 修订要点

| 原设计 | 修订后 | 原因 |
|--------|--------|------|
| 独立 ChromaDB 存储 | **复用 OpenClaw SQLite** | 官方已内置，无需额外依赖 |
| 独立反思引擎 | **对接 Dreaming** | Deep Phase 已实现，REM 可复用 |
| 独立检索系统 | **扩展 memory_search** | 官方已完善，补充跨 Agent 查询 |
| 独立 Web UI | **增强 Dreams UI** | 官方已有，补充跨 Agent 视图 |
| 从零构建 | **API 适配器模式** | 最小化重复工作 |

---

## OpenClaw 官方记忆系统分析

### 1. 双源记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                 OpenClaw Memory Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  动态记忆 (短期)                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  JSONL 会话日志                                      │   │
│  │  ~/.openclaw/agents/{agentId}/sessions/*.jsonl      │   │
│  │                                                      │   │
│  │  - 原始对话记录                                       │   │
│  │  - 自动追加，不压缩                                   │   │
│  │  - 不直接参与检索                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓ /new 或 flush                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  静态记忆 (长期) - Markdown                          │   │
│  │  ~/.openclaw/workspace/MEMORY.md                    │   │
│  │  ~/.openclaw/workspace/memory/YYYY-MM-DD.md         │   │
│  │                                                      │   │
│  │  - 会话摘要                                          │   │
│  │  - 用户偏好                                          │   │
│  │  - 重要决策                                          │   │
│  │  - 参与检索                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓ indexing                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SQLite 索引数据库                                   │   │
│  │  ~/.openclaw/memory/{agentId}.sqlite                │   │
│  │                                                      │   │
│  │  tables:                                             │   │
│  │  - files (元数据)                                    │   │
│  │  - chunks (文本块+embedding)                        │   │
│  │  - chunks_vec (向量) ← sqlite-vec                    │   │
│  │  - chunks_fts (全文) ← FTS5                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Dreaming 三阶段机制

```
┌─────────────────────────────────────────────────────────────┐
│                    Dreaming System                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Light    │ →  │    Deep     │ →  │    REM      │     │
│  │   Phase    │    │   Phase     │    │   Phase     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
│  阶段        │ 职责                    │ 写入位置           │
│  ─────────────────────────────────────────────────────────  │
│  Light       │ 读取短期信号，去重，     │ 无 (仅整理)        │
│              │ 暂存候选条目             │                   │
│  ─────────────────────────────────────────────────────────  │
│  Deep        │ 6 信号加权评分，         │ MEMORY.md         │
│              │ 达标则写入长期记忆       │ (追加)            │
│  ─────────────────────────────────────────────────────────  │
│  REM         │ 模式识别，主题提取，     │ DREAMS.md         │
│              │ 生成 Dream Diary        │ (叙事)            │
│                                                              │
│  触发方式:                                                   │
│  - 自动 cron (默认 03:00 每日)                              │
│  - 手动 /dreaming on                                        │
│  - openclaw memory promote                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Deep Ranking 六信号

| 信号 | 权重 | 说明 |
|------|------|------|
| Relevance | 0.30 | 平均检索质量 |
| Frequency | 0.24 | 短期信号累积次数 |
| Query diversity | 0.15 | 触发检索的独立查询数 |
| Recency | 0.15 | 时间衰减新鲜度 |
| Consolidation | 0.10 | 多日 recurrence 强度 |
| Conceptual richness | 0.06 | concept-tag 密度 |

---

## 跨 Agent 记忆共享层设计

### 核心思路

**不复制 OpenClaw 的存储，而是在其基础上构建共享访问层。**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Memory Sharing Gateway                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Storage Layer                          │  │
│  │                                                            │  │
│  │   OpenClaw SQLite          共享扩展表                      │  │
│  │   (官方内置)               (NEW)                          │  │
│  │   ┌──────────────┐         ┌──────────────┐              │  │
│  │   │ chunks      │         │ shared_mem  │              │  │
│  │   │ chunks_vec  │  ←──→   │ shared_acl  │              │  │
│  │   │ chunks_fts  │         │ agent_reg   │              │  │
│  │   └──────────────┘         └──────────────┘              │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↑                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Gateway API (REST)                      │  │
│  │                                                            │  │
│  │   POST /memory/store        存储共享记忆                    │  │
│  │   POST /memory/search       跨 Agent 检索                   │  │
│  │   GET  /memory/shared       获取共享记忆                    │  │
│  │   POST /memory/acl          设置访问控制                    │  │
│  │   GET  /agent/register     注册 Agent                     │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↑                                   │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│   │  OpenClaw │  │Claude Code│  │   Codex    │               │
│   │  Adapter  │  │ Adapter   │  │  Adapter   │               │
│   │  (原生)   │  │  (NEW)    │  │  (NEW)    │               │
│   └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 共享存储扩展 Schema

```sql
-- 共享记忆表
CREATE TABLE shared_memories (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  summary TEXT,
  type TEXT NOT NULL,          -- 'project' | 'global' | 'team'
  visibility TEXT NOT NULL,    -- 'private' | 'shared' | 'global'
  
  -- 来源
  source_agent TEXT NOT NULL,
  source_user TEXT,
  project_path TEXT,
  
  -- 评分
  importance REAL DEFAULT 5.0,
  confidence REAL DEFAULT 5.0,
  
  -- 时间
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  valid_until INTEGER,
  
  -- 向量 (复用 chunks_vec)
  chunk_id TEXT,
  
  -- 标签
  tags TEXT,                   -- JSON array
  
  FOREIGN KEY (chunk_id) REFERENCES chunks(id)
);

-- 访问控制表
CREATE TABLE shared_acl (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  permission TEXT NOT NULL,     -- 'read' | 'write' | 'admin'
  granted_by TEXT NOT NULL,
  granted_at INTEGER NOT NULL,
  FOREIGN KEY (memory_id) REFERENCES shared_memories(id)
);

-- Agent 注册表
CREATE TABLE agent_registry (
  agent_id TEXT PRIMARY KEY,
  agent_type TEXT NOT NULL,     -- 'openclaw' | 'claude_code' | 'codex'
  name TEXT,
  endpoint TEXT,                -- API endpoint 或 stdio path
  capabilities TEXT,            -- JSON: supported features
  last_seen INTEGER,
  created_at INTEGER NOT NULL
);

-- 索引
CREATE INDEX idx_shared_type ON shared_memories(type);
CREATE INDEX idx_shared_visibility ON shared_memories(visibility);
CREATE INDEX idx_acl_agent ON shared_acl(agent_id);
CREATE INDEX idx_shared_chunk ON shared_memories(chunk_id);
```

### Gateway API 设计

#### 存储共享记忆

```http
POST /api/v1/memory/shared/store
Content-Type: application/json
X-Agent-ID: claude_code_001

{
  "content": "这个项目使用 Python FastAPI，偏好类型注解",
  "type": "project",
  "visibility": "shared",
  "importance": 8,
  "tags": ["python", "fastapi", "preference"],
  "project_path": "/path/to/project"
}
```

#### 跨 Agent 检索

```http
POST /api/v1/memory/shared/search
Content-Type: application/json
X-Agent-ID: codex_001

{
  "query": "这个项目的 Python 编码规范",
  "limit": 10,
  "types": ["project", "global"],
  "project_path": "/path/to/project"
}
```

#### 响应格式

```json
{
  "results": [
    {
      "id": "shr_abc123",
      "content": "项目编码规范：使用 Black 格式化...",
      "type": "project",
      "source_agent": "openclaw",
      "score": 0.92,
      "snippet": "项目编码规范：使用 Black 格式化..."
    }
  ],
  "metadata": {
    "total": 1,
    "query_time_ms": 23,
    "agents_searched": ["openclaw", "claude_code"]
  }
}
```

---

## Claude Code / Codex 集成方案

### 方案概述

```
┌─────────────────────────────────────────────────────────────────┐
│              Claude Code / Codex Integration                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  方案: 通过 Memory Gateway API 访问 OpenClaw 记忆                 │
│                                                                  │
│  不修改 Claude Code / Codex 源码，                              │
│  而是通过环境变量 + 系统提示词增强实现集成                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Claude Code 集成

#### 方式 A: 系统提示词增强 (推荐)

```markdown
# 在 Claude Code 的 SYSTEM_PROMPT 或 .claude/commands/memory.md 中添加:

## Memory Integration
你可以通过 OpenClaw Memory Gateway 访问项目共享记忆:

记忆 API 地址: http://localhost:3045/api/v1

可用命令:
- `/memory search <query>` - 搜索项目共享记忆
- `/memory store <content> --type project --importance 8` - 存储重要记忆
- `/memory profile` - 查看用户画像

规则:
1. 开始新任务前，先搜索相关记忆
2. 重要决策完成后，存储到共享记忆
3. 优先读取共享记忆中的项目规范
```

#### 方式 B: Claude Code Custom Command

```markdown
# .claude/commands/share-memory.md

# Share to Project Memory

使用此命令将重要信息存储到项目共享记忆。

用法:
`/share-memory <content> [--importance 1-10] [--tags tag1,tag2]`

示例:
`/share-memory 这个模块使用策略模式，解耦了算法和调用方`

存储后，信息将对同一项目的所有 Agent 可见。
```

### Codex 集成

#### 环境变量配置

```bash
# .env 或系统环境变量
OPENCLAW_MEMORY_API=http://localhost:3045/api/v1
OPENCLAW_MEMORY_ENABLED=true
OPENCLAW_PROJECT_PATH=/path/to/current/project
```

#### Python 包装器

```python
# memory_client.py
import os
import requests
from typing import Optional

class OpenClawMemoryClient:
    def __init__(self, api_url: str = None):
        self.api_url = api_url or os.getenv("OPENCLAW_MEMORY_API", "http://localhost:3045/api/v1")
        self.project_path = os.getenv("OPENCLAW_PROJECT_PATH", ".")
    
    def search(self, query: str, limit: int = 5) -> list:
        """搜索项目共享记忆"""
        if not os.getenv("OPENCLAW_MEMORY_ENABLED"):
            return []
        
        try:
            resp = requests.post(
                f"{self.api_url}/memory/shared/search",
                json={"query": query, "limit": limit, "project_path": self.project_path},
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()["results"]
        except:
            pass
        return []
    
    def store(self, content: str, importance: int = 5, tags: list = None) -> bool:
        """存储到共享记忆"""
        if not os.getenv("OPENCLAW_MEMORY_ENABLED"):
            return False
        
        try:
            resp = requests.post(
                f"{self.api_url}/memory/shared/store",
                json={
                    "content": content,
                    "importance": importance,
                    "tags": tags or [],
                    "project_path": self.project_path,
                    "type": "project"
                },
                timeout=5
            )
            return resp.status_code == 200
        except:
            return False

# 全局实例
memory = OpenClawMemoryClient()

# 使用示例
if __name__ == "__main__":
    # 搜索
    results = memory.search("python 编码规范")
    for r in results:
        print(f"- {r['content']}")
    
    # 存储
    memory.store("使用 pytest 进行单元测试", importance=7, tags=["python", "testing"])
```

### 集成到 Agent 工作流

```
Claude Code / Codex 工作流:

1. 接收任务
       ↓
2. 搜索 OpenClaw 共享记忆 (通过 API)
       ↓
   ┌─────────────────────────────────────┐
   │  memory.search(query=任务描述)       │
   │  → 返回相关项目规范、历史决策、偏好   │
   └─────────────────────────────────────┘
       ↓
3. 结合记忆执行任务
       ↓
4. 任务完成后，存储重要成果到共享记忆
       ↓
   ┌─────────────────────────────────────┐
   │  memory.store(content=成果, ...)     │
   │  → 其他 Agent 下次可见              │
   └─────────────────────────────────────┘
```

---

## 实施路线图

### Phase 1: OpenClaw 增强 (Week 1-2)

```
目标: 在官方系统上增加共享层，不破坏现有功能

任务:
□ 分析 OpenClaw 源码，找到 SQLite 索引位置
□ 设计 shared_memories 等扩展表
□ 实现 Memory Gateway REST API
□ 添加 Agent 注册机制
□ 实现共享记忆的存储和检索 API
□ 测试与官方 Dreaming 系统的兼容性

交付物:
- Memory Gateway API 服务
- Agent 注册接口
- 共享存储 API
```

### Phase 2: Claude Code 适配器 (Week 3-4)

```
目标: 让 Claude Code 能读写 OpenClaw 记忆

任务:
□ 开发 Python memory_client 包装器
□ 编写 Claude Code 系统提示词模板
□ 开发 /memory 命令集
□ 实现自动记忆同步 (任务开始/结束时)
□ 测试多 Agent 并发访问

交付物:
- Claude Code Memory 适配器
- 使用文档
```

### Phase 3: Codex 适配器 (Week 5-6)

```
目标: 让 Codex 也能使用共享记忆

任务:
□ 开发 Codex 用 Python memory_client
□ 集成到 Codex 环境变量配置
□ 开发 Codex skill 模板
□ 实现跨平台 (Windows/Linux) 兼容
□ 测试 Codex + OpenClaw 协作场景

交付物:
- Codex Memory 适配器
- 环境配置指南
```

### Phase 4: UI 增强 (Week 7-8)

```
目标: 增强 Dreams UI，显示跨 Agent 记忆

任务:
□ 开发跨 Agent 记忆视图
□ 实现 ACL 管理界面
□ 开发 Dream Diary 增强版
□ 添加记忆统计和可视化
□ 实现记忆导入/导出功能

交付物:
- Dreams UI 增强版
- 记忆管理面板
```

---

## 与官方系统的分工

### 明确分工，避免重复

| 功能 | 负责方 | 说明 |
|------|--------|------|
| **本地 Markdown 记忆** | OpenClaw 官方 | MEMORY.md, memory/*.md |
| **SQLite 索引** | OpenClaw 官方 | chunks, chunks_vec, chunks_fts |
| **Dreaming 机制** | OpenClaw 官方 | Light/Deep/REM 三阶段 |
| **记忆检索工具** | OpenClaw 官方 | memory_search, memory_get |
| **Dreams UI** | OpenClaw 官方 | Gateway Dreams tab |
| **跨 Agent 共享** | **我们新增** | shared_memories 表, Gateway API |
| **Agent 适配器** | **我们新增** | Claude Code / Codex connector |
| **统一访问层** | **我们新增** | REST API, 访问控制 |
| **多 Agent 协调** | **我们新增** | agent_registry, ACL |

### 关键原则

1. **不修改 OpenClaw 官方文件** - 所有扩展用新表，不改官方 schema
2. **兼容官方升级** - 等待 OpenClaw 官方 release 后同步适配
3. **最小侵入** - 通过 API 和环境变量集成，不改源码
4. **本地优先** - 数据存在本地，不上云

---

## 附录

### A. OpenClaw 官方文档参考

- [Dreaming](https://docs.openclaw.ai/concepts/dreaming) - 梦境记忆系统
- [Builtin Memory Engine](https://docs.openclaw.ai/concepts/memory-builtin) - 内置存储引擎
- [Memory Search](https://docs.openclaw.ai/concepts/memory-search) - 检索系统
- [Memory Config](https://docs.openclaw.ai/reference/memory-config) - 配置参考

### B. 技术栈

| 组件 | 选择 | 原因 |
|------|------|------|
| 共享存储 | SQLite 扩展 | 与 OpenClaw 共用，简单 |
| API 框架 | FastAPI | 高性能，自动文档 |
| 向量 | 复用 OpenClaw sqlite-vec | 不重复 |
| 嵌入模型 | 复用 OpenClaw 配置 | 统一 |
| Web UI | 增强 Dreams UI | 不重复造轮子 |

### C. OpenClaw SQLite Schema (官方)

```sql
-- files: 索引文件元数据
CREATE TABLE files (
  path TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  hash TEXT NOT NULL,
  mtime INTEGER NOT NULL,
  size INTEGER NOT NULL
);

-- chunks: 文本块
CREATE TABLE chunks (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  source TEXT NOT NULL,
  start_line INTEGER,
  end_line INTEGER,
  hash TEXT NOT NULL,
  model TEXT NOT NULL,
  text TEXT NOT NULL,
  embedding TEXT NOT NULL,
  updated_at INTEGER
);

-- sqlite-vec 向量表
CREATE VIRTUAL TABLE chunks_vec USING vec0(...);

-- FTS5 全文索引
CREATE VIRTUAL TABLE chunks_fts USING fts5(...);
```

---

*修订版 - 基于 OpenClaw 2026.4.5 官方系统*
*项目路径: agent-memory-system/UNIVERSAL_ARCHITECTURE.md*
