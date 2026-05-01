# Agent Memory System

跨 Agent 记忆系统实战项目，用来沉淀经验、共享经验，并让不同 Agent 或工作流复用已有知识。

它适合这几类场景：

- 把一次解决过的问题沉淀成可复用经验
- 让多个 Agent 共享经验，而不是每次都从零开始
- 同时支持“共享经验库”和“本地私有记忆”两层能力
- 给后续的 Agent workflow、长期记忆、团队协作提供基础设施

## 核心能力

- 经验共享：把结构化经验写入云端 MySQL，供其他 Agent 查询和学习
- 本地记忆：支持本地 Agent 保存自己的偏好、上下文和工作记忆
- 双层存储：区分共享经验与私有记忆，避免混用
- Python SDK：可直接在 Python 项目里接入
- CLI 工具：支持命令行分享、搜索、获取、存储
- OpenClaw 适配：可作为 OpenClaw / Agent workflow 的记忆能力底座

## 适合解决什么问题

没有共享记忆时，常见问题是：

- 同类问题被多个 Agent 重复解决
- 经验只停留在聊天记录里，无法检索
- 一个 Agent 学到的东西，另一个 Agent 无法复用
- 本地偏好、共享经验、项目知识混在一起，边界不清

这个项目的思路是把问题拆成两层：

- 共享层：
  可复用、可引用、可搜索的经验
- 本地层：
  当前 Agent 的偏好、上下文、临时记忆

## 系统架构

```text
+--------------------------------------------------------------+
|                         Cloud MySQL                          |
|--------------------------------------------------------------|
| experiences                                                  |
| - shared experience metadata                                 |
| - markdown content                                           |
| - tags / domain / importance / author                        |
|                                                              |
| memories                                                     |
| - local or scoped memory                                     |
| - source agent                                               |
| - type / visibility / tags                                   |
+--------------------------------------------------------------+
                 ^                             ^
                 |                             |
        share / search API             local memory read/write
                 |                             |
         +-------+-----------------------------+-------+
         |                                             |
         |        Agent Memory Client / CLI / SDK      |
         |                                             |
         +---------------------------------------------+
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/kunpeng-ai-lab/agent-memory-system.git
cd agent-memory-system
```

### 2. 安装依赖

Windows:

```powershell
install.bat
```

Linux / macOS:

```bash
chmod +x install.sh
./install.sh
```

### 3. 准备 MySQL

确保你有一个可用的 MySQL 8.0+ 实例，然后创建数据库和用户：

```sql
CREATE DATABASE agent_memory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'memory_user'@'%' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON agent_memory.* TO 'memory_user'@'%';
FLUSH PRIVILEGES;
```

### 4. 配置数据库连接

推荐使用环境变量，而不是把密码直接写进配置文件。

PowerShell:

```powershell
$env:MEMORY_DB_HOST = "YOUR_MYSQL_HOST"
$env:MEMORY_DB_PORT = "3306"
$env:MEMORY_DB_DATABASE = "agent_memory"
$env:MEMORY_DB_USER = "memory_user"
$env:MEMORY_DB_PASSWORD = "YOUR_PASSWORD"
```

Linux / macOS:

```bash
export MEMORY_DB_HOST="YOUR_MYSQL_HOST"
export MEMORY_DB_PORT="3306"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="memory_user"
export MEMORY_DB_PASSWORD="YOUR_PASSWORD"
```

### 5. 初始化数据库

```bash
mysql -h YOUR_MYSQL_HOST -P 3306 -u memory_user -p agent_memory < scripts/init_mysql.sql

# 审核协作功能（首次安装或升级后运行）
mysql -h YOUR_MYSQL_HOST -P 3306 -u memory_user -p agent_memory < scripts/migration_review.sql
```

## 使用方式

### Python SDK

```python
from skills.agent-memory.scripts import ExperienceClient, MemoryClient

exp_client = ExperienceClient()

result = exp_client.share_experience(
    title="FastAPI 性能优化最佳实践",
    summary="uvicorn workers=4 在当前场景表现更稳定",
    content="# FastAPI 性能优化\n\n## workers 配置\n...",
    tags=["fastapi", "performance"],
    domain="BACKEND",
    importance=8.0
)

print(result["code"])

results = exp_client.search_experiences("fastapi 性能")
for item in results:
    print(item["code"], item["title"])

mem_client = MemoryClient()
mem_client.store_memory(
    content="用户偏好在下午处理复杂问题",
    memory_type="preference",
    tags=["user", "habit"]
)
```

### CLI

分享经验：

```bash
python -m skills.agent-memory.scripts.client share \
  --title "FastAPI 性能优化" \
  --summary "uvicorn workers=4" \
  --content "# FastAPI 性能优化..." \
  --tags fastapi,performance \
  --domain BACKEND
```

搜索经验：

```bash
python -m skills.agent-memory.scripts.client search "fastapi"
```

列出经验：

```bash
python -m skills.agent-memory.scripts.client list
```

获取详情：

```bash
python -m skills.agent-memory.scripts.client get EXP-BACKEND-FASTAPI-0001
```

存储本地记忆：

```bash
python -m skills.agent-memory.scripts.client store "记忆内容" --type preference
```

## 内容创作 Workflow

本系统沉淀的经验库，可直接作为内容创作的素材来源。以下是配套的三平台创作 SOP：

### 创作流程

1. **选题触发**：从 `experiences` 中提取有价值的技术经验（如"FastAPI workers 配置优化"）
2. **资料调研**：使用 Tavily Search 补充最新资料和权威参考
3. **三平台并行创作**：同一选题，产出三份角度风格完全不同的内容

### 三平台产出要求

| 平台 | 格式要求 | 风格 |
|------|----------|------|
| **博客** | 中英文双版（`.mdx` + `en-.mdx`） | SEO/GEO 深度技术文 |
| **小红书** | ≥5 张配图 + 口语化文案 | 种草向、场景化 |
| **公众号** | HTML 格式 + 封面图 | 观点输出、结构化 |

> 详细内容产出规范请参考 `docs/content-workflow.md`（如有）。

### 经验库创作示例

```bash
# 1. 从经验库搜索有分享价值的技术经验
python -m skills.agent-memory.scripts.client search "性能优化"

# 2. 获取经验详情
python -m skills.agent-memory.scripts.client get EXP-BACKEND-FASTAPI-0001

# 3. 将创作成果回填经验库
python -m skills.agent-memory.scripts.client share \
  --title "FastAPI 性能优化最佳实践（含三平台内容）" \
  --summary "workers=4 稳定，多平台验证" \
  --tags fastapi,performance,content \
  --domain BACKEND
```

## 数据模型

### experiences

共享经验库，适合沉淀“可复用的方法和经验”。

关键字段：

- `code`：唯一经验代码，例如 `EXP-BACKEND-FASTAPI-0001`
- `title`：经验标题
- `summary`：一句话摘要
- `content`：Markdown 正文
- `domain`：经验领域
- `tags`：标签列表
- `author_id`：作者标识
- `importance`：重要性评分

### memories

本地或作用域记忆，适合存 Agent 自己的上下文和偏好。

关键字段：

- `content`：记忆正文
- `summary`：摘要
- `md_content`：Markdown 正文
- `type`：记忆类型
- `visibility`：可见范围，支持 `private` / `shared` / `global`
- `source_agent`：来源 Agent
- `tags`：标签

### reviews

审核协作表，记录经验审核状态和批注。

关键字段：

- `experience_code`：被审核的经验 code
- `reviewer_id`：审核人 Agent ID
- `status`：审核状态（`requested` / `approved` / `changes_requested`）
- `decision`：审核决定（`approve` / `request_changes` / `reject`）
- `comment`：审核意见
- `line_reviews`：逐行批注（JSON）

### review_comments

逐行/逐字段批注表。

关键字段：

- `review_id`：所属 Review ID
- `line_number`：行号（针对特定行）
- `field_name`：字段名（针对特定字段）
- `comment`：批注内容
- `severity`：`suggestion` / `warning` / `error`

### activity_log

操作审计日志，记录所有协作操作。

关键字段：

- `actor_id`：操作者 Agent ID
- `action`：操作类型
- `target_type`：目标类型
- `target_id`：目标 ID

## 经验生命周期

```
draft → pending_review → published
                   ↘ revision_requested → (修改) → pending_review
                                                    ↘ archived
```

所有经验必须经过审核才能变为 `published` 状态，禁止作者自己批准自己。

## 经验编码规则

格式：

```text
EXP-{DOMAIN}-{TAG}-{SEQ:4}
```

示例：

```text
EXP-BACKEND-FASTAPI-0001
```

常用领域代码：

- `BACKEND`
- `FRONTEND`
- `DEVOPS`
- `AI`
- `DATABASE`
- `GENERAL`

## OpenClaw / Agent Workflow 触发思路

这个项目可以作为更大系统里的记忆能力模块。

### Agent 协作触发词

| 触发词/动作 | 执行结果 |
|------------|---------|
| `记住 xxx` | 写入本地 `memories` 表 |
| `分享经验` | 写入 `experiences` 表（draft）→ `request_review()` |
| `谁有 xxx 经验` | `search_experiences()` 查询 |
| `借鉴云端经验` | `get_experience()` 拉取内容 |
| `请审核 <code>` | 创建 Review，另一 Agent 执行 `submit_review()` |
| `批准 / 驳回` | 另一 Agent 调用 `submit_review(approve/reject)` |

> 完整的双 Agent 协作 SOP 请参考 [AGENT_SOP.md](./AGENT_SOP.md)，两个 Hermes Agent 加载此文件即可实现：写 → 发审核 → 提意见 → 改 → 批准 → 发布的完整协作闭环。

## 项目结构

```text
agent-memory-system/
├── scripts/
│   ├── init_mysql.sql          # 初始数据库 Schema
│   └── migration_review.sql    # Review 协作功能 Migration
├── skills/
│   └── agent-memory/
│       └── scripts/
│           ├── __init__.py
│           ├── config.py
│           ├── client.py       # ExperienceClient / MemoryClient / ReviewClient
│           └── review_cli.py   # 审核协作 CLI（request/submit/comment/pending）
├── src/
│   ├── core/
│   └── cli/
├── AGENT_SOP.md               # 给另一个 Agent 的固化协作规范
├── config.yaml.example
├── install.bat
├── install.sh
└── README.md
```

## 安全建议

- 不要把数据库密码直接写进仓库
- 尽量通过环境变量提供连接信息
- 生产环境建议启用 SSL/TLS
- MySQL 账户权限最小化，只授予 `agent_memory` 所需权限
- 定期轮换数据库密码

## 常见问题

### 数据库连接失败

优先检查：

- MySQL 服务是否启动
- 端口是否正确
- 账号和密码是否正确
- 防火墙或安全组是否放行

### PyMySQL 未安装

```bash
pip install pymysql
```

### 如何查看已分享经验

使用：

- `list_experiences()`
- 或 CLI 的 `list`

### 如何删除经验

使用 `delete_experience(code)`。

默认建议做软删除，而不是直接物理删除。

## 环境变量参考

| 变量名 | 说明 | 默认值 |
|---|---|---|
| `MEMORY_DB_HOST` | 数据库地址 | `localhost` |
| `MEMORY_DB_PORT` | 端口 | `3306` |
| `MEMORY_DB_DATABASE` | 数据库名 | `agent_memory` |
| `MEMORY_DB_USER` | 用户名 | - |
| `MEMORY_DB_PASSWORD` | 密码 | - |
| `MEMORY_DB_CHARSET` | 字符集 | `utf8mb4` |

## 贡献与反馈

欢迎分享、引用与改进。

- 发现问题：欢迎提交 [Issue](https://github.com/kunpeng-ai-lab/agent-memory-system/issues)
- 有改进建议：欢迎提交 [Pull Request](https://github.com/kunpeng-ai-lab/agent-memory-system/pulls)

## 相关链接

- 主站博客：https://kunpeng-ai.com
- GitHub 组织：https://github.com/kunpeng-ai-research
- OpenClaw 官方：https://openclaw.ai

## 维护与署名

- 维护者：鲲鹏AI探索局

## License

MIT
