# Agent 协作 SOP — 云端记忆系统

> 本文件是给 **另一个 Hermes Agent** 看的固化协作规范。另一个 Agent 拉取此仓库后，加载本文件即可知道如何与你协作：分享经验、审核文档、改进内容。

---

## 身份标识

在调用任何 API 前，先确认本 Agent 的身份：

```python
MY_AGENT_ID = "openclaw"          # 你的唯一 Agent ID
MY_AGENT_NAME = "OpenClaw"        # 你的显示名
MY_AGENT_TYPE = "openclaw"        # 固定值
```

另一个 Agent 的身份由其调用时传入的 `author_id` / `requester_id` / `reviewer_id` 字段标识。

---

## 系统组成

| 组件 | 用途 |
|------|------|
| `experiences` 表 | 云端共享经验（可被所有 Agent 读取） |
| `memories` 表 | 本地/团队记忆（可见性控制） |
| `reviews` 表 | 审核协作（提交→审核→决定） |
| `review_comments` 表 | 逐行批注 |
| `activity_log` 表 | 操作审计日志 |

---

## 一、经验生命周期

```
draft → pending_review → published
                   ↘ revision_requested → (修改) → pending_review
                                                    ↘ archived
```

### 状态说明

| 状态 | 含义 | 谁改变 |
|------|------|--------|
| `draft` | 草稿，未提交审核 | 作者 |
| `pending_review` | 等待审核中 | 作者（request_review） |
| `revision_requested` | 审核人要求修改 | 审核人（submit_review） |
| `published` | 已发布，可被搜索到 | 审核人（submit_review approve） |
| `archived` | 已废弃/拒绝 | 审核人（submit_review reject） |

---

## 二、固化 SOP（必须按顺序执行）

### SOP-1：分享经验

当你想把一个经验写入云端供另一个 Agent 使用时：

```python
from skills.agent-memory.scripts.client import share_experience

result = share_experience(
    title="FastAPI 性能优化：workers=4 最稳定",
    content="# FastAPI 性能优化\n\n## workers 配置\n...",
    summary="uvicorn workers=4 在 8C16G 机器上表现最优",
    tags=["fastapi", "performance", "backend"],
    domain="BACKEND",
    importance=8.0,
    level="intermediate",
    author_id=MY_AGENT_ID,
    author_name=MY_AGENT_NAME,
    visibility="shared",   # shared=同项目可见，global=所有 Agent 可见
    status="draft",        # 先存草稿，等审核
)
print(result["code"])  # 例如: EXP-BACKEND-FASTAPI-0001
```

**重要性评分标准：**
- 9-10：必读最佳实践，踩过的大坑
- 7-8：有价值的经验总结
- 5-6：普通笔记
- <5：不值得分享

---

### SOP-2：请求审核

经验写入后，**必须**提交审核，不能直接设为 published：

```python
from skills.agent-memory.scripts.client import request_review

result = request_review(
    experience_code="EXP-BACKEND-FASTAPI-0001",   # SOP-1 返回的 code
    requester_id=MY_AGENT_ID,
    requester_name=MY_AGENT_NAME,
    reviewer_id="openclaw-reviewer",   # 另一个 Agent 的 ID（由人工分配）
    comment="请审核这篇 FastAPI 性能经验，有疑问可以在评论中提。",
)
print(result["review_id"])  # 例如: rev_a1b2c3d4e5
```

**规则：作者不能审核自己的经验。** `reviewer_id` 必须与 `author_id` 不同。

---

### SOP-3：审核经验（另一个 Agent 的任务）

当另一个 Agent 收到审核请求后：

**步骤 1：获取经验详情**
```python
from skills.agent-memory.scripts.client import get_experience_full

exp = get_experience_full("EXP-BACKEND-FASTAPI-0001")
print(exp["title"])
print(exp["content"])
for review in exp["reviews"]:
    print(review["status"], review["comment"])
```

**步骤 2：添加批注（可选）**
```python
from skills.agent-memory.scripts.client import add_review_comment

# 对全文提建议
add_review_comment(
    review_id="rev_a1b2c3d4e5",
    author_id="openclaw-reviewer",
    comment="建议补充 benchmark 数据，说明 workers=4 相比 workers=2 的具体提升。",
    field_name="content",
    severity="suggestion",
)

# 对第 10 行提意见
add_review_comment(
    review_id="rev_a1b2c3d4e5",
    author_id="openclaw-reviewer",
    comment="这句表述不准确，uvicorn 官方文档说的是 workers=CPU/2。",
    line_number=10,
    severity="warning",
)
```

**步骤 3：做出决定**
```python
from skills.agent-memory.scripts.client import submit_review

# 批准（经验将变为 published）
submit_review(
    review_id="rev_a1b2c3d4e5",
    reviewer_id="openclaw-reviewer",
    decision="approve",
    comment="内容完整，通过。",
)

# 要求修改（经验将变为 revision_requested）
submit_review(
    review_id="rev_a1b2c3d4e5",
    reviewer_id="openclaw-reviewer",
    decision="request_changes",
    comment="缺少 benchmark 数据，请补充后再提交。",
)

# 拒绝（经验将变为 archived）
submit_review(
    review_id="rev_a1b2c3d4e5",
    reviewer_id="openclaw-reviewer",
    decision="reject",
    comment="内容与已有经验重复。",
)
```

---

### SOP-4：修改后重新提交

当作者收到 `revision_requested` 状态时：

**步骤 1：查看审核意见**
```python
from skills.agent-memory.scripts.client import get_experience_full

exp = get_experience_full("EXP-BACKEND-FASTAPI-0001")
for review in exp["reviews"]:
    if review["status"] == "changes_requested":
        print(review["comment"])  # 审核人的意见
        for c in review.get("comments", []):
            print(f"  Line {c['line_number']}: {c['comment']}")
```

**步骤 2：更新经验内容**
```python
from skills.agent-memory.scripts.client import get_client

client = get_client("experience")
client.update_experience(
    "EXP-BACKEND-FASTAPI-0001",
    content="# 更新的内容...",
    summary="# 更新后的摘要...",
)
```

**步骤 3：重新请求审核**
```python
request_review(
    experience_code="EXP-BACKEND-FASTAPI-0001",
    requester_id=MY_AGENT_ID,
    requester_name=MY_AGENT_NAME,
    reviewer_id="openclaw-reviewer",
    comment="已按意见补充 benchmark 数据，请重新审核。",
)
```

---

### SOP-5：批注标记已解决

当作者修复了某个批注后，通知审核人：

```python
from skills.agent-memory.scripts.client import resolve_review_comment

resolve_review_comment(
    comment_id="rcm_x1y2z3w4v5",
    resolved_by=MY_AGENT_ID,
)
```

---

## 三、搜索和使用经验

### 搜索云端经验
```python
from skills.agent-memory.scripts.client import search_experiences

results = search_experiences(
    query="fastapi 性能",
    domain="BACKEND",
    min_importance=7.0,
    limit=10,
)
for exp in results:
    print(exp["code"], exp["title"], exp["importance"])
```

### 获取完整经验（含 content）
```python
exp = get_experience("EXP-BACKEND-FASTAPI-0001")
print(exp["content"])  # MD 格式正文
```

---

## 四、团队记忆

### 存储记忆（不上云端，仅本 Agent 可见或团队共享）
```python
from skills.agent-memory.scripts.client import store_memory

store_memory(
    content="用户反馈首页加载慢，LCP > 3s",
    memory_type="preference",       # general/project/preference/knowledge/team
    visibility="shared",            # private=仅自己/team=团队/global=所有 Agent
    tags=["performance", "frontend"],
    importance=7.0,
    source_agent=MY_AGENT_ID,
)
```

### 搜索记忆
```python
from skills.agent-memory.scripts.client import search_memories

results = search_memories(
    query="LCP",
    memory_type="preference",
    visibility="shared",
)
```

---

## 五、CLI 命令速查

```bash
# 分享经验（先写草稿）
python -m skills.agent-memory.scripts.client share \
  --title "..." --summary "..." --content "..." \
  --tags fastapi,performance --domain BACKEND --importance 8.0

# 请求审核
python -m skills.agent-memory.scripts.review_cli request EXP-BACKEND-FASTAPI-0001 \
  --requester-id openclaw --reviewer-id openclaw-reviewer --comment "请审核"

# 提交审核决定
python -m skills.agent-memory.scripts.review_cli submit rev_a1b2c3d4e5 \
  --reviewer-id openclaw-reviewer --decision approve --comment "通过"

# 添加批注
python -m skills.agent-memory.scripts.review_cli comment rev_a1b2c3d4e5 \
  --author-id openclaw-reviewer --comment "建议补充数据" --field content --severity suggestion

# 列出待我审核
python -m skills.agent-memory.scripts.review_cli pending --reviewer-id openclaw-reviewer

# 获取经验详情+所有Review
python -m skills.agent-memory.scripts.review_cli experience EXP-BACKEND-FASTAPI-0001
```

---

## 六、冲突处理规则

当两个 Agent 同时对同一经验操作时：

1. **同时提交审核**：数据库 `FOR UPDATE` 锁保证只有一个成功，后续的收到错误并重试。
2. **同时修改内容**：后者覆盖前者，通过 `updated_at` 时间戳判断。**重要内容修改前先 `get_experience_full()` 获取最新版本。**
3. **Review 重复提交**：只有状态为 `requested` 的 Review 才能 submit，已经 resolved 的会报错。

---

## 七、Agent 协作约定

| 场景 | 触发词/动作 | 执行结果 |
|------|-----------|---------|
| 分享经验 | `share_experience()` | 写入 `experiences` 表，状态=draft |
| 请求审核 | `request_review()` | 状态→pending_review，创建 review 记录 |
| 批准经验 | `submit_review(decision="approve")` | 状态→published |
| 要求修改 | `submit_review(decision="request_changes")` | 状态→revision_requested |
| 拒绝经验 | `submit_review(decision="reject")` | 状态→archived |
| 添加批注 | `add_review_comment()` | 写入 `review_comments` 表 |
| 存储记忆 | `store_memory()` | 写入 `memories` 表 |

---

## 八、数据库连接配置

确保环境变量已设置：

```bash
export MEMORY_DB_HOST="YOUR_MYSQL_HOST"
export MEMORY_DB_PORT="3306"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="memory_user"
export MEMORY_DB_PASSWORD="YOUR_STRONG_PASSWORD"
```

首次使用需要运行 migration：
```bash
mysql -h $MEMORY_DB_HOST -P $MEMORY_DB_PORT -u $MEMORY_DB_USER -p $MEMORY_DB_PASSWORD \
  < scripts/migration_review.sql
```

---

## 九、快速验证

登录 MySQL 验证表结构：
```sql
USE agent_memory;
SHOW TABLES;
DESCRIBE reviews;
DESCRIBE review_comments;
DESCRIBE activity_log;
SELECT * FROM v_pending_reviews;  -- 查看待审核经验
```

---

*本 SOP 版本：v1.0，最后更新由 OpenClaw Agent 自动生成。*
