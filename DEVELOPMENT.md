# Agent Memory System - 开发计划 (客户版)

**版本:** v3.0  
**日期:** 2026-04-07  
**存储:** MySQL 5.7+ / SQLite (云端)

---

## 1. 系统概述

Agent Memory System 是一个**跨 Agent 共享记忆系统**，让 OpenClaw、Claude Code、Codex、Kimi Code、Cursor 等 Coding Agent 能够：

- ✅ **共享项目知识** - 团队编码规范、设计模式
- ✅ **记住用户偏好** - 编程风格、工具偏好
- ✅ **积累项目经验** - 常见问题、解决方案
- ✅ **跨 Agent 协作** - 一个 Agent 学到的，其他 Agent 也能用

---

## 2. 存储方案选择

| 方案 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **MySQL** | 有云端数据库的团队 | 高并发、数据安全 | 需要 MySQL 服务 |
| **SQLite** | 小团队/个人 | ⭐ 零配置、简单 | 并发一般 |

### 推荐

| 客户情况 | 推荐方案 |
|----------|----------|
| 有云端 MySQL | MySQL 5.7 或 8.0 |
| 不想用数据库 | SQLite (云服务器文件共享) |
| 不确定 | SQLite (最简单的开始方式) |

---

## 3. 一键安装

### Linux / macOS

```bash
curl -fsSL https://xxx/install.sh | bash
```

### Windows

```powershell
irm https://xxx/install.ps1 | iex
```

### 或者手动安装

```bash
# 1. 下载 CLI
curl -fsSL -o memory https://xxx/memory
chmod +x memory

# 2. 配置 (SQLite 示例)
mkdir -p ~/.memory
cat > ~/.memory/config.yaml << EOF
database:
  type: sqlite
  path: ~/.memory/memory.db
EOF

# 3. 使用
./memory status
./memory store "我的第一个记忆"
./memory search "第一个"
```

---

## 4. 快速开始

### 基本命令

```bash
# 存储记忆
memory store "项目使用 FastAPI 框架" --type project --tags python,fastapi

# 搜索记忆
memory search "fastapi"

# 列出所有记忆
memory list

# 查看状态
memory status

# 获取帮助
memory --help
```

### 在 OpenClaw 中使用

```
Agent: /memory store "这个项目用 pytest 测试"
Agent: /memory search "测试"
```

### 在 Claude Code 中使用

```
/memory store "模块使用策略模式" --type project
/memory search "策略模式"
```

---

## 5. 开发阶段

### Phase 1: 核心功能 (Week 1-2)

| 任务 | 说明 |
|------|------|
| MySQL 5.7 连接池 | 支持云端 MySQL |
| SQLite 适配器 | 支持文件共享 |
| CLI 工具 | store/search/list/get/delete |
| 一键安装脚本 | 自动配置 |

**里程碑:** `memory store "test" && memory search "test"` 正常工作

### Phase 2: OpenClaw 插件 (Week 3-4)

| 任务 | 说明 |
|------|------|
| OpenClaw Skill | `/memory` 命令 |
| 配置同步 | 自动读取 OpenClaw 配置 |
| Web UI | 可视化管理 |

### Phase 3: 其他 Agent 适配 (Week 5-7)

| Agent | 适配方式 |
|-------|----------|
| Claude Code | Command |
| Codex | Python 模块 |
| Kimi Code | 配置 |
| Cursor | MCP |

### Phase 4: API 服务 (Week 8-9)

| 功能 | 说明 |
|------|------|
| REST API | HTTP 接口 |
| API 认证 | Key 认证 |
| Web 管理 | 可视化界面 |

### Phase 5: 向量搜索 (Week 10-11)

| 功能 | 说明 |
|------|------|
| 语义搜索 | 理解意图 |
| 混合搜索 | 关键词 + 向量 |
| 性能优化 | 缓存、索引 |

### Phase 6: 生产部署 (Week 12)

| 任务 | 说明 |
|------|------|
| 安全审计 | 权限、加密 |
| 备份恢复 | 数据安全 |
| 文档完善 | 用户指南 |

---

## 6. 文件结构

```
agent-memory-system/
├── src/
│   ├── core/              # 核心引擎
│   │   ├── config.py      # 配置管理
│   │   ├── models.py      # 数据模型
│   │   ├── database.py    # MySQL/SQLite 适配器
│   │   ├── store.py       # 存储引擎
│   │   └── search.py      # 搜索引擎
│   ├── cli/
│   │   ├── memory_cli.py  # CLI 主程序
│   │   └── memory_sdk.py  # Python SDK
│   └── adapters/          # 各平台适配器
│
├── scripts/
│   ├── install.sh         # Linux/macOS 安装
│   ├── install.ps1        # Windows 安装
│   └── init_mysql.sql    # MySQL 初始化
│
├── config.yaml.example    # 配置示例
├── requirements.txt       # Python 依赖
└── README.md
```

---

## 7. 配置说明

### MySQL 配置

```yaml
database:
  type: mysql
  host: "218.201.18.131"    # 你的 MySQL 地址
  port: 8999                  # 端口
  database: "agent_memory"  # 数据库名
  user: "root1"              # 用户名
  password: "your-password"  # 密码
  pool:
    min_size: 5
    max_size: 20
```

### SQLite 配置

```yaml
database:
  type: sqlite
  path: "~/.memory/memory.db"  # 数据库文件路径
```

---

## 8. 常见问题

### Q: 需要安装 MySQL 吗？

**A:** 不需要。系统支持两种模式：
- **MySQL** - 如果你已经有云端 MySQL，直接配置连接即可
- **SQLite** - 不需要任何数据库服务，文件存储

### Q: 多台电脑如何共享？

**A:** 两种方式：
1. **MySQL** - 所有电脑连接同一个云端数据库
2. **SQLite** - 将数据库文件放在云服务器/ NAS，通过 SMB/NFS 共享

### Q: 非技术人员能安装吗？

**A:** 可以。一键安装脚本会自动检测环境并配置。平均安装时间 < 5 分钟。

### Q: 支持哪些 Agent？

**A:** 目前支持：
- OpenClaw (已规划)
- Claude Code (已规划)
- Codex (已规划)
- Kimi Code (已规划)
- Cursor (已规划)

---

## 9. 技术支持

- **文档:** [README.md](README.md)
- **问题反馈:** [Issues](../../issues)
- **讨论:** [Discussions](../../discussions)

---

## 10. 里程碑

| 周数 | 里程碑 | 验收标准 |
|------|--------|----------|
| Week 2 | ⭐ 核心功能 | `memory store` + `search` 正常 |
| Week 4 | OpenClaw 插件 | Skill 可用 |
| Week 7 | 四平台适配 | 四种 Agent 均可用 |
| Week 9 | REST API | HTTP 接口可用 |
| Week 11 | 向量搜索 | 语义搜索可用 |
| Week 12 | v1.0 发布 | 生产就绪 |

---

*开发计划 v3.0 - 面向客户，低门槛*
