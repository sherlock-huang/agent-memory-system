# Agent Memory System - Adapters
## 跨平台 Agent 适配器

**版本:** 1.0.0  
**存储:** 云端 MySQL (agent_memory)

---

## 概述

本目录包含各 Coding Agent 的适配器，让它们能够共享同一个记忆库：

| Agent | 适配方式 | 状态 |
|--------|----------|------|
| OpenClaw | Skill 插件 | ✅ |
| Claude Code | Command | ✅ |
| Codex | Python 模块 | ✅ |
| Kimi Code | YAML 配置 | ✅ |
| Cursor | MCP Server | ✅ |

---

## 快速安装

### OpenClaw

1. 复制适配器到 OpenClaw 目录：
```bash
cp -r adapters/openclaw ~/.openclaw/skills/memory-share
```

2. 重启 OpenClaw

3. 使用命令：
```
/memory store "内容" --type project
/memory search "查询"
```

### Claude Code

1. 复制命令到 Claude Code 目录：
```bash
cp -r adapters/claude_code/commands ~/.claude/
```

2. 在 Claude Code 中使用：
```
/memory store "内容"
```

### Codex

1. 复制模块到 Codex：
```bash
cp adapters/codex/memory.py ~/.codex/
```

2. 在代码中使用：
```python
from memory import memory
memory.store("内容", type="project")
```

### Kimi Code

1. 复制配置到 Kimi：
```bash
cp adapters/kimi/config.yaml ~/.kimi/config/memory.yaml
```

2. 配置环境变量：
```bash
export MYSQL_PASSWORD="your-password"
```

### Cursor

1. 复制 MCP 配置到 Cursor：
```bash
cp adapters/cursor/mcp_settings.json ~/.cursor/mcp-settings.json
```

2. 在 Cursor 设置中启用 MCP

---

## 配置

所有适配器共用同一个 MySQL 数据库：

```yaml
database:
  type: mysql
  host: "218.201.18.131"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "your-password"
```

---

## 目录结构

```
adapters/
├── openclaw/
│   ├── SKILL.md           # OpenClaw Skill 说明
│   ├── memory_skill.py    # Python 包装器
│   ├── memory.exe         # Windows CLI 包装器
│   └── memory.cmd         # Windows Batch
│
├── claude_code/
│   └── commands/
│       └── memory.md      # Claude Code 命令
│
├── codex/
│   └── memory.py          # Codex Python 模块
│
├── kimi/
│   └── config.yaml       # Kimi 配置
│
└── cursor/
    └── mcp_settings.json # Cursor MCP 配置
```

---

## 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `project` | 项目相关 | 项目规范、技术栈 |
| `preference` | 用户偏好 | 沟通风格 |
| `knowledge` | 知识积累 | 解决方案 |
| `team` | 团队共享 | 团队规范 |
| `general` | 通用 | 其他 |

---

## 常见问题

### Q: 多台电脑如何共享记忆？

A: 所有 Agent 连接同一个云端 MySQL 数据库，记忆自动共享。

### Q: 需要安装 MySQL 吗？

A: 不需要，记忆系统使用已有的云端 MySQL。

### Q: 如何查看记忆状态？

A: 使用 `/memory status` 或 `memory.status()`。

---

*由 Agent Memory System 提供*
