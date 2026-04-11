# 内容创作与审核工作流 SOP

**版本**: v1.0  
**日期**: 2026-04-11  
**适用场景**: AI 内容创作（小红书、公众号、博客）的小山→山海审核流程

---

## 1. 角色定义

| 角色 | Agent ID | 职责 |
|------|----------|------|
| 小山 | `xiaoshan` | 内容生成者，负责创作初稿 |
| 山海 | `shanhai` | 审核者，负责内容质量把关 |

---

## 2. 内容状态机

```
[DRAFT] --> [PENDING_REVIEW] --> [NEEDS_REVISION] --> [PENDING_REVIEW] --> [APPROVED] --> [PUBLISHED]
                 |                      ^
                 |______________________|
                        (feedback)
```

| 状态 | 标签 | 说明 |
|------|------|------|
| `draft` | `content:draft` | 草稿，未提交审核 |
| `pending_review` | `content:pending_review` | 待审核 |
| `needs_revision` | `content:needs_revision` | 需修改（附反馈） |
| `approved` | `content:approved` | 审核通过，待发布 |
| `published` | `content:published` | 已发布 |

---

## 3. 经验写入规范

### 3.1 内容经验格式

```
标题: {平台}-{主题}-{版本}
  例如: 小红书-AI大模型发展趋势-v1

Tags (必须包含):
  - content:{status}          # 当前状态
  - platform:{平台}           # 小红书/抖音/公众号/b站/博客
  - author:{agent_id}         # 作者 agent
  - reviewer:{agent_id}       # 审核人 agent
  - workflow                  # 标记为工作流内容

Content (JSON 格式):
{
  "platform": "小红书",
  "title": "AI大模型发展趋势",
  "outline": "...大纲...",
  "content": "...正文...",
  "cover_text": "...封面文案...",
  "hashtags": ["#AI", "#大模型"],
  "language": "zh",
  "notes": "..."
}

Summary: 一句话内容描述
Visibility: shared
Importance: 7.0
```

### 3.2 反馈经验格式

```
标题: 反馈-{原内容标题}-{版本}
  例如: 反馈-小红书-AI大模型发展趋势-v1

Tags (必须包含):
  - content:feedback
  - ref:{原内容ID}
  - feedback_for:{原内容code}
  - reviewer:{agent_id}

Content (JSON 格式):
{
  "original_id": "...",
  "original_code": "...",
  "approved": false,
  "overall_score": 6.5,
  "scores": {
    "title": 7.0,
    "content": 6.0,
    "cover": 7.0,
    "hashtags": 6.5
  },
  "strengths": ["...", "..."],
  "issues": [
    {"section": "开头", "issue": "...", "suggestion": "..."},
    {"section": "结尾", "issue": "...", "suggestion": "..."}
  ],
  "summary": "总体建议..."
}

Visibility: shared
Importance: 8.0
```

---

## 4. 审核标准

### 4.1 评分维度 (0-10)

| 维度 | 说明 | 权重 |
|------|------|------|
| `title` | 标题吸引力 | 20% |
| `content` | 内容质量（信息量、逻辑性） | 40% |
| `cover` | 封面/配图文案 | 20% |
| `hashtags` | 标签/话题选择 | 10% |
| `platform_fit` | 平台适配度 | 10% |

### 4.2 审核结论

| 结论 | 条件 | 操作 |
|------|------|------|
| `approved` | 综合分 ≥ 7.0 | 直接通过 |
| `needs_revision` | 综合分 4.0-6.9 | 反馈问题，等待修改 |
| `rejected` | 综合分 < 4.0 | 需重新创作 |

---

## 5. 数据库配置

### 环境变量设置

```bash
# Linux/macOS
export MEMORY_DB_HOST="218.201.18.131"
export MEMORY_DB_PORT="8999"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="root1"
export MEMORY_DB_PASSWORD='lJ0)sG0\dI1~gN1"lJ6|'

# Windows (PowerShell)
$env:MEMORY_DB_HOST = "218.201.18.131"
$env:MEMORY_DB_PORT = "8999"
$env:MEMORY_DB_DATABASE = "agent_memory"
$env:MEMORY_DB_USER = "root1"
$env:MEMORY_DB_PASSWORD = "lJ0)sG0\dI1~gN1`"lJ6|"
```

### 配置文件 (config.yaml)

```yaml
database:
  type: "mysql"
  host: "${MEMORY_DB_HOST}"
  port: "${MEMORY_DB_PORT}"
  database: "${MEMORY_DB_DATABASE}"
  user: "${MEMORY_DB_USER}"
  password: "${MEMORY_DB_PASSWORD}"
  charset: "utf8mb4"

agent:
  id: null      # 自动生成
  name: "昆仑"
  type: "openclaw"

experience:
  default_visibility: "shared"
  default_importance: 5.0
  default_level: "intermediate"
```

---

## 6. 工作流详细步骤

### Step 1: 小山生成内容 → 存入待审核

```python
from src.core.store import StoreEngine
import json

store = StoreEngine()

content = {
    "platform": "小红书",
    "title": "AI大模型发展趋势",
    "outline": "...",
    "content": "...",
    "cover_text": "...",
    "hashtags": ["#AI", "#大模型"],
    "language": "zh"
}

memory = store.store(
    content=json.dumps(content, ensure_ascii=False),
    share_title="小红书-AI大模型发展趋势-v1",
    tags=["content:pending_review", "platform:小红书", "author:xiaoshan", "workflow"],
    visibility="shared",
    importance=7.0
)

print(f"待审核内容ID: {memory.id}")
```

### Step 2: 山海查询待审核内容

```python
from src.core.store import StoreEngine

store = StoreEngine()

# 搜索待审核内容
results = store.db.search_memories(
    query="content:pending_review platform:小红书",
    limit=10
)

# 获取详情
for memory in results:
    print(f"ID: {memory.id}")
    print(f"标题: {memory.share_title}")
    print(f"作者: {memory.source_agent}")
    print(f"标签: {memory.tags}")
```

### Step 3: 山海写入审核反馈

```python
feedback = {
    "original_id": "mem_xxxxxxxxxx",
    "approved": False,
    "overall_score": 6.5,
    "scores": {
        "title": 7.0,
        "content": 6.0,
        "cover": 7.0,
        "hashtags": 6.5
    },
    "strengths": ["标题吸引力不错", "信息量充足"],
    "issues": [
        {
            "section": "开头",
            "issue": "开场太生硬",
            "suggestion": "建议用痛点/问题引入"
        }
    ],
    "summary": "整体不错，小修改后可通过"
}

feedback_memory = store.store(
    content=json.dumps(feedback, ensure_ascii=False),
    share_title=f"反馈-{original_title}",
    tags=["content:feedback", f"ref:{original_id}", "reviewer:shanhai", "workflow"],
    visibility="shared",
    importance=8.0
)
```

### Step 4: 小山读取反馈 → 修改 → 重新提交

```python
# 读取反馈
feedbacks = store.db.search_memories(
    query=f"ref:{content_id} content:feedback",
    limit=5
)

# 根据反馈修改内容
# ... 修改逻辑 ...

# 更新状态为 pending_review（重新提交）
store.update(
    memory_id=content_id,
    tags=["content:pending_review", "platform:小红书", "author:xiaoshan", "workflow", "revision:2"]
)
```

---

## 7. 使用示例

### 小山的完整流程

```
用户: 帮我写一篇小红书，关于"AI大模型发展趋势"
↓
小山: 生成内容 → 存入云端（pending_review）
↓
小山: 通知山海审核，告知 ID
↓
山海: 读取内容 → 审核评分 → 写入反馈
↓
小山: 读取反馈 → 修改内容 → 重新提交
↓
山海: 再次审核 → approved
↓
小山: 发布到小红书
```

---

## 8. 注意事项

1. **Tag 规范**: 所有内容经验必须包含 `workflow` 标签，方便检索
2. **反馈关联**: 每条反馈必须包含 `ref:{原内容ID}` 和 `feedback_for:{原内容code}`
3. **版本管理**: 修改后的版本追加 `revision:N` 标签
4. **可见性**: 内容在审核期间设为 `shared`，审核人才能看到
5. **Agent ID**: 各 Agent 需要设置唯一的 `source_agent`，如 `xiaoshan` / `shanhai`
