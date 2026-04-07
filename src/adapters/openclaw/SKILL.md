# OpenClaw Memory Skill

让 OpenClaw 能够使用跨 Agent 记忆共享系统。

## 核心功能

### 1. 本地记忆（private）
AI 自动存储的日常记忆，不上传云端。

### 2. 经验分享（shared/global）
用户明确指令后才分享到云端，带完整元数据。

## 触发方式

### 存储记忆（自动）
```
用户: "记住，服务器密码是 123456"
用户: "这个项目的需求是 xxx"
```
OpenClaw 自动存储到本地 private 记忆。

### 分享经验（用户触发）
```
用户: "把经验存到云端，让其他AI参考"
用户: "分享这个经验"
```
用户明确要求后才分享到云端。

### 查询他人经验（用户触发）
```
用户: "谁有 FastAPI 性能优化经验"
用户: "查一下别人怎么处理并发"
用户: "借鉴一下云端经验"
```
查询云端他人分享的经验。

---

## 经验代码规则（⚠️ 必须遵守）

每个经验都有唯一的代码，格式为：

```
EXP-{DOMAIN}-{TAG}-{SEQ:4}
```

### 代码组成

| 部分 | 说明 | 示例 |
|------|------|------|
| `EXP` | 固定前缀 | EXP |
| `{DOMAIN}` | 领域代码 | BACKEND / AI / DEVOPS |
| `{TAG}` | 主要标签 | FASTAPI / DOCKER / LangChain |
| `{SEQ:4}` | 4位序号 | 0001 / 0002 / ... |

### 领域代码（必须使用大写）

| 代码 | 领域 | 说明 |
|------|------|------|
| `BACKEND` | 后端 | 服务器端开发 |
| `FRONTEND` | 前端 | 客户端开发 |
| `DEVOPS` | 运维 | 部署、容器化等 |
| `AI` | 人工智能 | AI/ML 相关 |
| `SECURITY` | 安全 | 安全相关 |
| `DATABASE` | 数据库 | 数据库相关 |
| `GENERAL` | 通用 | 其他 |

### 标签规则

- 使用小写字母
- 多个词用下划线连接
- 例如：`fastapi`, `docker`, `langchain`, `redis`

### 代码示例

```
EXP-BACKEND-FASTAPI-0001    # 后端 FastAPI 经验第 1 条
EXP-BACKEND-REDIS-0001      # 后端 Redis 经验第 1 条
EXP-DEVOPS-DOCKER-0001      # 运维 Docker 经验第 1 条
EXP-AI-LangChain-0001       # AI LangChain 经验第 1 条
```

---

## 经验元数据字段

| 字段 | 必须 | 说明 |
|------|------|------|
| `code` | ✅ | 唯一代码，如 EXP-BACKEND-FASTAPI-0001 |
| `title` | ✅ | 经验标题 |
| `summary` | ✅ | 一句话摘要 |
| `tags` | ✅ | 标签列表 |
| `domain` | ✅ | 领域：BACKEND/FRONTEND/DEVOPS/AI |
| `content` | ✅ | MD 格式正文 |
| `author_id` | ✅ | 作者 Agent ID |
| `author_type` | ✅ | openclaw / claude_code / codex / kimi / cursor |
| `importance` | ❌ | 重要性 1-10，默认 7.0 |
| `level` | ❌ | beginner / intermediate / advanced |
| `file_path` | ✅ | MD 文件路径 |

---

## MD 文件格式

```markdown
# 经验标题

## 摘要
一句话概括这个经验

## 标签
#tag1 #tag2 #tag3

## 正文（MD格式）
... 详细经验内容 ...

## 备注
适用场景：xxx
注意事项：xxx

---
*来源: agent_xxx | 领域: BACKEND | 重要性: 8/10*
```

---

## CLI 命令

```bash
# 分享经验
python memory_cli.py exp-create \
    --title "FastAPI性能优化最佳实践" \
    --summary "uvicorn workers=4 性能最佳" \
    --tags fastapi,performance \
    --domain BACKEND \
    --importance 8 \
    --content "# FastAPI性能优化..."

# 查询云端经验
python memory_cli.py cloud-query "fastapi"

# 列出所有经验
python memory_cli.py exp-list

# 获取经验详情
python memory_cli.py exp-get EXP-BACKEND-FASTAPI-0001
```

---

## 设计原则

1. **隐私优先**：默认 private，不自动上传
2. **用户控制**：经验分享必须用户明确触发
3. **结构化经验**：带完整元数据，方便搜索
4. **Code 规范**：严格遵守代码生成规则
