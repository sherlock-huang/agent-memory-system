# Agent Memory System - 新版使用指南

## 快速开始

### 1. 安装/更新 Skill

在 OpenClaw workspace 中执行：

**Linux/macOS:**
```bash
cd ~/.openclaw/workspace
git clone https://github.com/kunpeng-ai-lab/agent-memory-system.git
cd agent-memory-system
./install.sh
```

**Windows:**
```cmd
cd %USERPROFILE%\.openclaw\workspace
git clone https://github.com/kunpeng-ai-lab/agent-memory-system.git
cd agent-memory-system
install.bat
```

### 2. 配置数据库连接

**必须配置环境变量**（不配置会导致无法使用）：

```bash
# Linux/macOS
export MEMORY_DB_HOST="你的MySQL地址"
export MEMORY_DB_PORT="3306"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="你的用户名"
export MEMORY_DB_PASSWORD="你的密码"

# Windows PowerShell
$env:MEMORY_DB_HOST = "你的MySQL地址"
$env:MEMORY_DB_PASSWORD = "你的密码"
```

**重要**：
- 密码不要写在配置文件中，只用环境变量
- 数据库需要先执行 `scripts/init_mysql.sql` 初始化

### 3. 初始化数据库

```bash
mysql -h 你的MySQL地址 -u 用户名 -p agent_memory < scripts/init_mysql.sql
```

### 4. 在 OpenClaw 中使用

新版 skill 默认启动后，直接用自然语言即可：

| 场景 | 说法示例 |
|------|----------|
| 分享经验 | "把刚才的 FastAPI 部署经验存到云端" |
| 查询经验 | "谁有 Docker 性能优化的经验？" |
| 获取经验 | "获取 EXP-DEVOPS-DOCKER-0001 的详情" |
| 存储记忆 | "记住用户喜欢用暗色模式" |

---

## 经验代码规则

格式：`EXP-{领域}-{标签}-{序号:4位}`

| 领域代码 | 说明 |
|----------|------|
| BACKEND | 后端开发 |
| FRONTEND | 前端开发 |
| DEVOPS | 运维/容器 |
| AI | 人工智能 |
| DATABASE | 数据库 |
| GENERAL | 通用 |

---

## Python SDK 用法

```python
from skills.agent-memory.scripts import ExperienceClient, MemoryClient

# 初始化
exp_client = ExperienceClient()  # 自动读取环境变量

# 分享经验到云端
result = exp_client.share_experience(
    title="FastAPI 部署最佳实践",
    summary="使用 gunicorn + uvicorn 性能最优",
    content="# FastAPI 部署\n\n## 环境配置\n...",
    tags=["fastapi", "deployment", "gunicorn"],
    domain="BACKEND",
    importance=8.0
)
print(f"经验代码: {result['code']}")

# 搜索云端经验
results = exp_client.search_experiences("fastapi 部署")
for exp in results:
    print(f"[{exp['code']}] {exp['title']} - {exp['summary']}")

# 获取完整经验（包含 MD 正文）
exp = exp_client.get_experience("EXP-BACKEND-FASTAPI-0001")
print(exp['content'])

# 存储本地记忆（不上传云端）
mem_client = MemoryClient()
mem_client.store_memory(
    content="用户项目使用 Python 3.11 + FastAPI",
    memory_type="project",
    visibility="private",
    tags=["project", "tech-stack"]
)
```

---

## 常见问题

**Q: 报错 "数据库未配置"**
A: 需要设置 `MEMORY_DB_HOST`、`MEMORY_DB_USER`、`MEMORY_DB_PASSWORD` 等环境变量

**Q: 报错 "PyMySQL 未安装"**
A: 运行 `pip install pymysql`

**Q: 如何查看所有云端经验？**
A: `exp_client.list_experiences(domain="BACKEND")`

---

## 文件位置

```
agent-memory-system/
├── skills/agent-memory/
│   ├── SKILL.md              # 完整技能文档
│   └── scripts/
│       ├── config.py         # 配置管理
│       ├── client.py         # Python SDK
│       └── status.py         # 状态检查
├── scripts/init_mysql.sql    # 数据库初始化
└── config.yaml.example       # 配置示例
```
