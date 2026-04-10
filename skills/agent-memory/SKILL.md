---
name: agent-memory
description: |
  跨Agent经验共享技能 - 存储和获取云端经验
  激活场景: 用户提到"分享经验"、"查询云端经验"、"借鉴经验"、"记住xxx"时使用
  此技能默认启动，让OpenClaw天然支持上传和读取云端经验
---

# Agent Memory Skill - 经验共享技能

让 OpenClaw 能够存储和获取云端经验。

## 功能概述

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 存储经验 | 将经验存入云端 MySQL | "分享经验"、"上传云端" |
| 查询经验 | 搜索云端已有经验 | "谁有xxx经验"、"查一下云端" |
| 获取经验 | 获取单条经验详情 | "获取经验EXP-xxx" |
| 存储记忆 | 本地存储记忆（不上传） | "记住xxx" |

## 核心概念

### 经验 vs 记忆

| 类型 | 说明 | 存储位置 |
|------|------|----------|
| **经验** | 可分享给其他 Agent 的知识 | 云端 MySQL |
| **记忆** | Agent 本地私有记忆 | 本地 MySQL |

### 经验代码规则

每个经验有唯一代码，格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

**领域代码（必须大写）：**
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

## 数据库配置

### 首次配置

如果未配置数据库连接，Agent 会自动提示用户输入：

```
请提供 MySQL 数据库连接信息：
1. 数据库地址（host）
2. 端口（port，默认 3306）
3. 数据库名（database，默认 agent_memory）
4. 用户名（user）
5. 密码（password）- 不会明文存储
```

### 配置存储

敏感信息通过环境变量存储，不在配置文件中明文保存：

```bash
# 设置环境变量（不推荐明文写在脚本中）
$env:MEMORY_DB_HOST = "your-mysql-host.com"
$env:MEMORY_DB_PORT = "3306"
$env:MEMORY_DB_DATABASE = "agent_memory"
$env:MEMORY_DB_USER = "your_username"
$env:MEMORY_DB_PASSWORD = "your_password"
```

### 配置文件格式 (config.yaml)

```yaml
# 数据库配置（从环境变量读取）
database:
  host: "${MEMORY_DB_HOST}"
  port: "${MEMORY_DB_PORT:-3306}"
  database: "${MEMORY_DB_DATABASE:-agent_memory}"
  user: "${MEMORY_DB_USER}"
  password: "${MEMORY_DB_PASSWORD}"
  charset: "utf8mb4"

# Agent 配置
agent:
  id: "kunlun"
  name: "昆仑"
  type: "openclaw"

# 搜索配置
search:
  default_limit: 10
  max_limit: 100
```

## 使用方法

### 1. 分享经验到云端

当用户说"分享经验"、"上传到云端"等时：

```python
# 调用示例
from skills.agent-memory.scripts.client import ExperienceClient

client = ExperienceClient()
client.share_experience(
    title="FastAPI性能优化最佳实践",
    summary="uvicorn workers=4 性能最佳",
    content="# FastAPI性能优化...\n\n## workers配置\n...",
    tags=["fastapi", "performance", "uvicorn"],
    domain="BACKEND",
    importance=8.0
)
```

### 2. 查询云端经验

当用户说"谁有xxx经验"、"查一下云端"等时：

```python
# 搜索经验
results = client.search_experiences(
    query="fastapi 性能",
    domain="BACKEND",
    limit=10
)

for exp in results:
    print(f"[{exp['code']}] {exp['title']}")
    print(f"摘要: {exp['summary']}")
    print(f"---")
```

### 3. 获取单条经验

```python
# 获取经验详情
exp = client.get_experience("EXP-BACKEND-FASTAPI-0001")
print(exp['content'])  # MD 格式正文
```

### 4. 列出所有云端经验

```python
# 列出经验
experiences = client.list_experiences(
    domain="BACKEND",
    limit=50
)
```

### 5. 存储本地记忆（不上传）

```python
# 存储私有记忆
client.store_memory(
    content="用户喜欢在下午处理复杂问题",
    memory_type="preference",
    tags=["user", "habit"]
)
```

### 6. 搜索本地记忆

```python
# 搜索记忆
memories = client.search_memories(
    query="用户习惯",
    visibility="private"
)
```

## CLI 命令

```bash
# 初始化数据库
mysql -h YOUR_HOST -P YOUR_PORT -u YOUR_USER -p agent_memory < scripts/init_mysql.sql

# 分享经验
python -m skills.agent-memory.scripts.client share \
    --title "标题" \
    --summary "摘要" \
    --content "MD内容" \
    --tags fastapi,performance \
    --domain BACKEND

# 查询经验
python -m skills.agent-memory.scripts.client search "关键词"

# 列出经验
python -m skills.agent-memory.scripts.client list --domain BACKEND

# 获取经验
python -m skills.agent-memory.scripts.client get EXP-BACKEND-FASTAPI-0001

# 存储记忆
python -m skills.agent-memory.scripts.client store "记忆内容" --type preference
```

## 触发词汇总

### 分享经验触发词
- "把这个经验存到云端"
- "分享经验"
- "上传到云端"
- "让其他AI也能学到"

### 查询经验触发词
- "谁有xxx经验"
- "查一下云端"
- "借鉴经验"
- "参考别人的做法"

### 存储记忆触发词
- "记住xxx"
- "存到记忆"
- "这个信息很重要"

## 数据库表结构

### experiences 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 内部ID (mem_xxx) |
| code | VARCHAR(50) | 经验代码 (EXP-BACKEND-XXX-0001) |
| title | VARCHAR(200) | 经验标题 |
| summary | VARCHAR(500) | 一句话摘要 |
| content | MEDIUMTEXT | **MD格式正文（核心）** |
| domain | VARCHAR(50) | 领域 |
| tags | JSON | 标签列表 |
| author_id | VARCHAR(100) | 作者ID |
| importance | DECIMAL(3,1) | 重要性 1-10 |
| created_at | BIGINT | 创建时间戳 |

### memories 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 记忆ID |
| content | TEXT | 记忆内容 |
| summary | VARCHAR(500) | 摘要 |
| md_content | MEDIUMTEXT | **MD格式正文** |
| type | ENUM | 类型 (general/project/preference/knowledge/team) |
| visibility | ENUM | 可见性 (private/shared/global) |
| source_agent | VARCHAR(100) | 来源Agent |
| importance | DECIMAL(3,1) | 重要性 |
| tags | JSON | 标签 |
| created_at | BIGINT | 创建时间戳 |

## 注意事项

1. **敏感信息安全**：数据库密码通过环境变量传递，不写在配置文件或代码中
2. **默认不上传**：记忆默认 private，不自动上传云端
3. **用户控制**：经验分享需要用户明确触发
4. **MD格式**：content 字段存储完整的 Markdown 格式内容

## 项目路径

```
{AGENT_MEMORY_PATH}/                          # 项目根目录
├── scripts/
│   └── init_mysql.sql                        # 数据库初始化脚本
├── skills/
│   └── agent-memory/
│       ├── SKILL.md                          # 本文件
│       └── scripts/
│           ├── __init__.py
│           ├── config.py                     # 配置管理
│           └── client.py                     # Python客户端
└── config.yaml.example                       # 配置示例
```
