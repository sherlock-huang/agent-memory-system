# Agent Memory System

跨 Agent 记忆共享系统，支持 OpenClaw、Claude Code、Codex、Kimi Code、Cursor 等 AI 工具。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 核心功能

### 1. 本地记忆（默认 private）
AI 自动存储的日常记忆，不上传云端。

### 2. 经验分享（shared/global）
用户明确指令后才分享到云端，带完整元数据和 MD 文件。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     MySQL (元数据)                          │
│  • code, title, summary, tags, domain                      │
│  • author, importance, quality_score                        │
│  • file_path (指向 MD 文件)                                  │
├─────────────────────────────────────────────────────────────┤
│                    文件存储 (MD 文件)                        │
│  /experiences/2026-04/EXP-BACKEND-FASTAPI-0001.md           │
│  • 完整的 Markdown 内容                                      │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装

```bash
# Windows
install.bat

# Linux/macOS
chmod +x install.sh && ./install.sh
```

### 2. 基本使用

```bash
# 查看状态
python src/cli/memory_cli.py status

# 存储记忆（默认 private，不上传）
python src/cli/memory_cli.py store "这是一个本地记忆" --type general

# 分享经验到云端（用户触发）
python src/cli/memory_cli.py exp-create \
    --title "FastAPI性能优化最佳实践" \
    --summary "uvicorn workers=4 性能最佳" \
    --tags fastapi,performance \
    --domain BACKEND \
    --importance 8 \
    --content "# FastAPI性能优化\n\n..."

# 查询云端经验
python src/cli/memory_cli.py cloud-query "FastAPI性能"

# 列出所有经验
python src/cli/memory_cli.py exp-list
```

## 经验代码规则

每个经验有唯一代码，格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

| 部分 | 说明 | 示例 |
|------|------|------|
| `EXP` | 固定前缀 | EXP |
| `{DOMAIN}` | 领域 | BACKEND / AI / DEVOPS |
| `{TAG}` | 主要标签 | FASTAPI / DOCKER |
| `{SEQ:4}` | 序号 | 0001 |

### 领域代码

| 代码 | 领域 |
|------|------|
| `BACKEND` | 后端 |
| `FRONTEND` | 前端 |
| `DEVOPS` | 运维 |
| `AI` | 人工智能 |
| `SECURITY` | 安全 |
| `DATABASE` | 数据库 |
| `GENERAL` | 通用 |

### 示例

```
EXP-BACKEND-FASTAPI-0001
EXP-DEVOPS-DOCKER-0001
EXP-AI-LangChain-0001
```

## OpenClaw 触发词

| 用户输入 | OpenClaw 动作 |
|---------|--------------|
| `记住xxx` | 存储到本地记忆 |
| `分享经验` | 分享经验到云端 |
| `谁有xxx经验` | 查询云端经验 |
| `查一下云端` | 列出共享经验 |

## 项目结构

```
agent-memory-system/
├── src/
│   ├── core/
│   │   ├── config.py          # 配置管理
│   │   ├── models.py          # Memory 模型
│   │   ├── experience.py       # Experience 模型
│   │   ├── file_storage.py     # 文件存储
│   │   ├── database.py         # 数据库入口
│   │   ├── store.py            # 存储引擎
│   │   └── search.py           # 搜索引擎
│   ├── cli/
│   │   ├── memory_cli.py       # CLI 主程序
│   │   └── experience_cli.py   # 经验管理
│   └── adapters/              # 各 Agent 适配器
├── scripts/
│   ├── init_mysql.sql         # MySQL 初始化
│   └── init_experiences.sql    # 经验表
├── install.bat / install.sh    # 安装脚本
├── config.yaml               # 配置文件
└── README.md
```

## 数据库

- **memories**: 本地记忆
- **experiences**: 经验（带 MD 文件索引）

## 设计原则

1. **隐私优先**：默认 private，不自动上传
2. **用户控制**：经验分享必须用户明确触发
3. **结构化**：带完整元数据和代码，方便搜索
4. **文件存储**：MD 原生格式，Agent 容易理解
