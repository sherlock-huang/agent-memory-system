# Agent Memory System

跨 Agent 经验共享系统，支持将经验上传到云端 MySQL 存储，其他 Agent 可下载学习。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     云端服务器                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     MySQL                                │    │
│  │         端口: YOUR_MYSQL_PORT (默认 3306)                │    │
│  │         数据库: agent_memory                            │    │
│  │         - experiences 表（经验元数据 + MD内容）         │    │
│  │         - memories 表（Agent 本地记忆）                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                    Agent 请求 (PyMySQL)
```

## 快速安装

### 第一步：服务器部署（云端管理人员执行，一次性）

```bash
# 连接到云服务器
ssh root@YOUR_SERVER_IP

# 安装 MySQL 8.0+
# Ubuntu:
apt update && apt install mysql-server
mysql_secure_installation

# CentOS:
yum install mysql-server
systemctl start mysqld
mysql_secure_installation

# 创建数据库和用户
mysql -u root -p <<EOF
CREATE DATABASE agent_memory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'memory_user'@'%' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON agent_memory.* TO 'memory_user'@'%';
FLUSH PRIVILEGES;
EOF
```

### 第二步：客户端安装

```bash
# 克隆项目
git clone https://github.com/sherlock-huang/agent-memory-system.git
cd agent-memory-system

# Windows 安装
install.bat

# Linux/macOS 安装
chmod +x install.sh && ./install.sh
```

### 第三步：配置数据库连接

**方式一：环境变量（推荐，最安全）**

```powershell
# PowerShell
$env:MEMORY_DB_HOST = "YOUR_MYSQL_HOST"
$env:MEMORY_DB_PORT = "3306"
$env:MEMORY_DB_DATABASE = "agent_memory"
$env:MEMORY_DB_USER = "memory_user"
$env:MEMORY_DB_PASSWORD = "YOUR_PASSWORD"
```

```bash
# Linux/macOS
export MEMORY_DB_HOST="YOUR_MYSQL_HOST"
export MEMORY_DB_PORT="3306"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="memory_user"
export MEMORY_DB_PASSWORD="YOUR_PASSWORD"
```

**方式二：配置文件（不推荐，敏感信息会明文存储）**

复制并编辑 `config.yaml.example` 为 `config.yaml`：

```yaml
database:
  host: "YOUR_MYSQL_HOST"
  port: 3306
  database: "agent_memory"
  user: "memory_user"
  password: "YOUR_PASSWORD"  # 不推荐！
```

### 第四步：初始化数据库

```bash
# 执行初始化脚本
mysql -h YOUR_MYSQL_HOST -P 3306 -u memory_user -p agent_memory < scripts/init_mysql.sql
```

## 使用方法

### Python SDK

```python
from skills.agent-memory.scripts import ExperienceClient, MemoryClient

# 初始化客户端（自动从环境变量读取配置）
exp_client = ExperienceClient()

# 分享经验到云端
result = exp_client.share_experience(
    title="FastAPI性能优化最佳实践",
    summary="uvicorn workers=4 性能最佳",
    content="# FastAPI性能优化\n\n## workers配置\n...",
    tags=["fastapi", "performance"],
    domain="BACKEND",
    importance=8.0
)
print(f"经验代码: {result['code']}")

# 搜索云端经验
results = exp_client.search_experiences("fastapi 性能")
for exp in results:
    print(f"[{exp['code']}] {exp['title']}")

# 获取经验详情（包含完整MD内容）
exp = exp_client.get_experience("EXP-BACKEND-FASTAPI-0001")
print(exp['content'])

# 存储本地记忆（不上传）
mem_client = MemoryClient()
mem_client.store_memory(
    content="用户喜欢在下午处理复杂问题",
    memory_type="preference",
    tags=["user", "habit"]
)
```

### CLI 命令

```bash
# 分享经验
python -m skills.agent-memory.scripts.client share \
    --title "FastAPI性能优化" \
    --summary "uvicorn workers=4" \
    --content "# FastAPI性能优化..." \
    --tags fastapi,performance \
    --domain BACKEND

# 搜索经验
python -m skills.agent-memory.scripts.client search "fastapi"

# 列出所有经验
python -m skills.agent-memory.scripts.client list

# 获取经验详情
python -m skills.agent-memory.scripts.client get EXP-BACKEND-FASTAPI-0001

# 存储记忆
python -m skills.agent-memory.scripts.client store "记忆内容" --type preference
```

## 经验代码规则

每个经验有唯一代码，格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

| 部分 | 说明 | 示例 |
|------|------|------|
| `EXP` | 固定前缀 | EXP |
| `{DOMAIN}` | 领域 | BACKEND / DEVOPS / AI |
| `{TAG}` | 主要标签 | FASTAPI / DOCKER / LangChain |
| `{SEQ:4}` | 序号 | 0001 |

### 领域代码

| 代码 | 领域 |
|------|------|
| `BACKEND` | 后端 |
| `FRONTEND` | 前端 |
| `DEVOPS` | 运维 |
| `AI` | 人工智能 |
| `DATABASE` | 数据库 |
| `GENERAL` | 通用 |

## OpenClaw 触发词

| 用户输入 | OpenClaw 动作 |
|---------|--------------|
| `记住xxx` | 存储到本地记忆 |
| `分享经验` | 分享经验到云端 |
| `谁有xxx经验` | 查询云端经验 |
| `借鉴云端经验` | 下载并学习云端经验 |

## 项目结构

```
agent-memory-system/
├── scripts/
│   ├── init_mysql.sql          # MySQL 初始化脚本
│   └── init_experiences.sql    # 经验表（已合并到init_mysql.sql）
├── skills/
│   └── agent-memory/
│       ├── SKILL.md            # 技能说明
│       └── scripts/
│           ├── __init__.py
│           ├── config.py       # 配置管理
│           └── client.py       # Python 客户端
├── src/
│   ├── core/                   # 核心模块（保留）
│   └── cli/                    # CLI（保留）
├── config.yaml.example         # 配置示例
├── install.bat / install.sh    # 安装脚本
└── README.md
```

## 数据库表结构

### experiences 表（核心）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(50) | 内部ID (mem_xxx) |
| `code` | VARCHAR(50) | 唯一代码 (EXP-BACKEND-FASTAPI-0001) |
| `title` | VARCHAR(200) | 经验标题 |
| `summary` | VARCHAR(500) | 一句话摘要 |
| **`content`** | **MEDIUMTEXT** | **MD格式正文（核心内容）** |
| `domain` | VARCHAR(50) | 领域 |
| `tags` | JSON | 标签列表 |
| `author_id` | VARCHAR(100) | 作者ID |
| `importance` | DECIMAL(3,1) | 重要性 1-10 |
| `created_at` | BIGINT | 创建时间戳 |

### memories 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(50) | 记忆ID |
| `content` | TEXT | 记忆内容 |
| `summary` | VARCHAR(500) | 摘要 |
| `md_content` | MEDIUMTEXT | MD格式正文 |
| `type` | ENUM | 类型 |
| `visibility` | ENUM | 可见性 (private/shared/global) |
| `source_agent` | VARCHAR(100) | 来源Agent |
| `tags` | JSON | 标签 |
| `created_at` | BIGINT | 创建时间戳 |

## 安全注意事项

1. **数据库密码不要写在配置文件中**，使用环境变量
2. MySQL 用户权限最小化，只授权 `agent_memory` 数据库
3. 生产环境建议启用 SSL/TLS 加密连接
4. 定期更新数据库密码

## 常见问题

### Q: 数据库连接失败
A: 检查：
- MySQL 服务是否运行
- 端口是否正确（默认 3306）
- 用户名密码是否正确
- 防火墙是否放行

### Q: PyMySQL 未安装
A: 运行：`pip install pymysql`

### Q: 如何查看已分享的经验？
A: 使用 `list_experiences()` 方法或 CLI 的 `list` 命令

### Q: 如何删除经验？
A: 使用 `delete_experience(code)` 方法，默认软删除（改为 archived 状态）

## 环境变量参考

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMORY_DB_HOST` | 数据库地址 | localhost |
| `MEMORY_DB_PORT` | 端口 | 3306 |
| `MEMORY_DB_DATABASE` | 数据库名 | agent_memory |
| `MEMORY_DB_USER` | 用户名 | - |
| `MEMORY_DB_PASSWORD` | 密码 | - |
| `MEMORY_DB_CHARSET` | 字符集 | utf8mb4 |

## 贡献与反馈

欢迎分享、引用与改进。

- 发现问题：欢迎提交 Issue
- 有改进建议：欢迎提交 Pull Request

## 项目作者与维护

- 作者 / 维护者：Sherlock Huang
- 项目仓库：https://github.com/sherlock-huang/agent-memory-system
- 项目定位：跨 Agent 记忆系统实战项目，用于经验沉淀、共享与复用

## License

MIT
