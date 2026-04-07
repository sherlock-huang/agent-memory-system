---
name: agent-memory
description: 跨 Agent 记忆共享系统，支持存储本地记忆和分享经验到云端。
---

# Agent Memory System 技能

跨 Agent 记忆共享系统，让 AI 能够：
- 存储本地记忆（不上传云端）
- 分享经验到云端供其他 AI 使用
- 查询和借鉴云端他人分享的经验

## 基本概念

### 记忆 vs 经验

| 类型 | 说明 | 上传方式 |
|------|------|----------|
| **记忆** | AI 本地记忆 | 自动存储，private |
| **经验** | 重要经验分享 | 用户触发后上传云端 |

### 经验代码规则

每个经验有唯一代码，格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

**领域代码：**
- `BACKEND` - 后端开发
- `FRONTEND` - 前端开发
- `DEVOPS` - 运维/容器
- `AI` - 人工智能
- `DATABASE` - 数据库
- `GENERAL` - 通用

**示例：**
```
EXP-BACKEND-FASTAPI-0001
EXP-DEVOPS-DOCKER-0001
EXP-AI-LangChain-0001
```

## 触发命令

### 存储记忆

用户说以下内容时，自动存储到本地记忆：
- "记住 xxx"
- "存到记忆 xxx"

```
python src/cli/memory_cli.py store "内容" --type general --tags tag1,tag2
```

### 分享经验

用户说以下内容时，触发经验分享：
- "把经验存到云端"
- "分享这个经验"

```
python src/cli/memory_cli.py share-experience \
    --title "经验标题" \
    --summary "一句话摘要" \
    --tags fastapi,performance \
    --importance 8 \
    "完整的 MD 格式经验内容..."
```

### 查询云端经验

用户说以下内容时，查询云端经验：
- "谁有 xxx 经验"
- "查一下云端"
- "借鉴经验"

```
python src/cli/memory_cli.py cloud-query "关键词"
```

### 列出经验

```
python src/cli/memory_cli.py list-shared
python src/cli/memory_cli.py my-experiences
```

## CLI 路径

```
~/.openclaw/workspace/agent-memory-system/src/cli/memory_cli.py
```

## 状态检查

```
python ~/.openclaw/workspace/agent-memory-system/src/cli/memory_cli.py status
```

## 设计原则

1. **隐私优先**：默认 private，不自动上传
2. **用户控制**：经验分享必须用户明确触发
3. **结构化**：带完整元数据和代码，方便搜索
