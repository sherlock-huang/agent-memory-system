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
git clone https://github.com/sherlock-huang/agent-memory-system.git
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

例如：

- `记住 xxx`
  写入本地记忆
- `分享经验`
  写入共享经验库
- `谁有 xxx 经验`
  查询共享经验
- `借鉴云端经验`
  拉取共享经验用于当前任务

## 项目结构

```text
agent-memory-system/
├── scripts/
│   └── init_mysql.sql
├── skills/
│   └── agent-memory/
│       ├── SKILL.md
│       └── scripts/
│           ├── __init__.py
│           ├── config.py
│           └── client.py
├── src/
│   ├── core/
│   └── cli/
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

- 发现问题：欢迎提交 [Issue](https://github.com/sherlock-huang/agent-memory-system/issues)
- 有改进建议：欢迎提交 [Pull Request](https://github.com/sherlock-huang/agent-memory-system/pulls)

## 相关链接

- 主站博客：https://kunpeng-ai.com
- GitHub 组织：https://github.com/kunpeng-ai-research
- OpenClaw 官方：https://openclaw.ai

## 维护与署名

- 维护者：鲲鹏AI探索局

## License

MIT
