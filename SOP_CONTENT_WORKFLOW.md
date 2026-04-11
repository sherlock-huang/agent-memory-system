# 内容创作与审核工作流 SOP

> 本文档描述「小山」与「山海」协作完成内容创作的完整流程。

## 角色分工

| 角色 | Agent ID | 职责 |
|------|----------|------|
| **小山** | `xiao_shan` | 内容创作、修改、发布 |
| **山海** | `shanhai` | 审核内容、给反馈、评分 |

---

## 工具与环境

### 环境变量配置

在每个 Agent 的运行环境中设置以下环境变量：

```bash
# 数据库配置
export MEMORY_DB_HOST="218.201.18.131"
export MEMORY_DB_PORT="8999"
export MEMORY_DB_DATABASE="agent_memory"
export MEMORY_DB_USER="root1"
export MEMORY_DB_PASSWORD='lJ0)sG0\dI1~gN1"lJ6|'
```

> ⚠️ **密码不明文存储**：通过环境变量注入，不要写入配置文件或代码。

### 依赖安装

```bash
pip install pymysql pyyaml
```

---

## 工作流总览

```
┌──────────────────────────────────────────────────────────────┐
│                        内容创作工作流                           │
└──────────────────────────────────────────────────────────────┘

  小山（创作者）                          山海（审核者）
      │                                        │
      │  1. 创作内容                            │
      │  ───────── 草稿存入 DB ────────→         │
      │                                        │
      │  2. 提交审核                            │
      │  ──────── 状态: pending ───────→        │
      │                                        │
      │                              ←── 3. 获取待审核列表
      │                                        │
      │                              ←── 4. 审核评分 + 写反馈
      │                                        │
      │  5. 查看反馈                            │
      │  ←───────── 反馈写入 DB ────────         │
      │                                        │
      │  6. 修改内容（可选）                      │
      │  ───────── 重新提交 ──────────→          │
      │                                        │
      │  7. 发布（审核通过后）                    │
      │  ───────── 状态: published ────→         │
      │                                        │
```

---

## 详细步骤

### Step 1: 小山创作内容

**触发词**："帮我写一篇小红书"、"生成内容"、"写公众号文章"

**小山执行**：

```python
from skills.content_creation.scripts import store_content

# 创作并保存草稿
result = store_content(
    platform="小红书",
    title="AI大模型发展的5个趋势",
    content="...",
    cover_text="2024年AI会变成什么样？",
    hashtags=["#AI", "#人工智能", "#科技趋势"],
    author_id="xiao_shan",
    author_name="小山"
)
print(f"草稿已保存: {result['id']}")
```

**标签**：`content:draft`、`platform:小红书`、`author:xiao_shan`

---

### Step 2: 小山提交审核

**触发词**："提交审核"、"送审"

**小山执行**：

```python
from skills.content_creation.scripts import submit_for_review

# 提交审核（会自动创建草稿，如果还没有的话）
result = submit_for_review(
    content_id="mem_xxxxxxxxxx",  # 草稿 ID
    platform="小红书",
    title="AI大模型发展的5个趋势",
    content="...",
    cover_text="2024年AI会变成什么样？",
    hashtags=["#AI", "#人工智能", "#科技趋势"],
    author_id="xiao_shan",
    author_name="小山"
)
print(f"已提交: {result['status']}")
```

**状态变化**：`content:draft` → `content:pending_review`

---

### Step 3: 山海获取待审核列表

**触发词**："有新的待审核内容吗"、"查看审核队列"

**山海执行**：

```python
from skills.content_review.scripts.api import list_pending_review

pending = list_pending_review(limit=10)
print(f"待审核: {len(pending)} 条")
for item in pending:
    print(f"  [{item.id}] {item.share_title}")
    tags = [t for t in item.tags if t.startswith('platform:')]
    print(f"    平台: {tags}")
```

---

### Step 4: 山海审核并写反馈

**触发词**："审核这条内容"、"评分"

**山海执行**：

```python
from skills.content_review.scripts.api import (
    get_content_by_id,
    submit_feedback
)

# 获取内容详情
content = get_content_by_id("mem_xxxxxxxxxx")
print(f"标题: {content['title']}")
print(f"正文: {content['content']}")
print(f"封面: {content['cover_text']}")
print(f"标签: {content['hashtags']}")

# 审核评分并提交反馈
feedback = submit_feedback(
    content_id="mem_xxxxxxxxxx",
    scores={
        "title": 7.5,
        "content": 6.0,
        "cover": 7.0,
        "hashtags": 6.5,
        "platform_fit": 7.0
    },
    issues=[
        {
            "section": "开头",
            "issue": "开场太生硬",
            "suggestion": "建议用痛点/问题引入"
        },
        {
            "section": "结尾",
            "issue": "缺少行动号召",
            "suggestion": "添加'关注我获取更多...'类语句"
        }
    ],
    summary="整体不错，小修改后可通过",
    strengths=["标题吸引力不错", "信息量充足"],
    approved=False,
    reviewer_id="shanhai"
)
print(f"反馈已提交: {feedback.id}")
```

**评分标准**：

| 维度 | 权重 | 说明 |
|------|------|------|
| title | 20% | 标题吸引力 |
| content | 40% | 内容质量 |
| cover | 20% | 封面文案 |
| hashtags | 10% | 标签选择 |
| platform_fit | 10% | 平台适配度 |

**审核结论**：

| 综合分 | 结论 | 操作 |
|--------|------|------|
| ≥7.0 | ✅ 通过 | 状态改为 `content:approved` |
| 4.0-6.9 | ⚠️ 需修改 | 状态改为 `content:needs_revision` |
| <4.0 | ❌ 需重写 | 状态改为 `content:draft` |

---

### Step 5: 小山查看反馈

**触发词**："查看审核反馈"、"审核意见是什么"

**小山执行**：

```python
from skills.content_creation.scripts import get_feedback_for_content

feedbacks = get_feedback_for_content("mem_xxxxxxxxxx")
for fb in feedbacks:
    data = json.loads(fb.content)
    print(f"审核人: {data['reviewer']}")
    print(f"综合分: {data['overall_score']}")
    print(f"总体评价: {data['summary']}")
    print(f"优点: {data['strengths']}")
    print(f"问题:")
    for issue in data['issues']:
        print(f"  - [{issue['section']}] {issue['issue']}")
        print(f"    建议: {issue['suggestion']}")
```

---

### Step 6: 小山修改内容

**触发词**："根据反馈修改"、"修改后重新提交"

**小山执行**：

1. 根据反馈修改内容
2. 重新提交审核

```python
from skills.content_creation.scripts import submit_for_review

# 修改后的内容重新提交
result = submit_for_review(
    content_id="mem_xxxxxxxxxx",  # 同一 ID，会更新状态
    platform="小红书",
    title="AI大模型发展的5个趋势（修订版）",
    content="...（修改后的正文）...",
    cover_text="2024年AI发展趋势揭秘",
    hashtags=["#AI", "#人工智能", "#科技趋势", "#AI大模型"],
    author_id="xiao_shan",
    author_name="小山"
)
```

---

### Step 7: 小山发布内容

**触发词**："标记已发布"、"内容发布了"

**小山执行**：

```python
from skills.content_review.scripts.api import mark_published

success = mark_published("mem_xxxxxxxxxx")
print(f"已标记发布: {success}")
```

**状态变化**：`content:approved` → `content:published`

---

## 标签系统

### 状态标签

| 标签 | 说明 |
|------|------|
| `content:draft` | 草稿 |
| `content:pending_review` | 待审核 |
| `content:needs_revision` | 需修改 |
| `content:approved` | 审核通过 |
| `content:published` | 已发布 |

### 平台标签

| 标签 | 说明 |
|------|------|
| `platform:小红书` | 小红书 |
| `platform:抖音` | 抖音 |
| `platform:公众号` | 微信公众号 |
| `platform:b站` | B站 |
| `platform:博客` | 博客 |

### 角色标签

| 标签 | 说明 |
|------|------|
| `author:xiao_shan` | 小山创作 |
| `author:shanhai` | 山海审核 |
| `reviewer:shanhai` | 审核人 |

### 修订标签

| 标签 | 说明 |
|------|------|
| `revision:1` | 第一轮修订 |
| `revision:2` | 第二轮修订 |

---

## 经验代码规范

经验代码格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

例如：
- `EXP-CONTENT-XIAOSHAN-0001`
- `EXP-CONTENT-SHANHAI-0001`

---

## 常见问题

### Q: 环境变量在哪里设置？

**A**: 在每个 Agent 的启动脚本或配置中设置。如果使用 OpenClaw，在 `config.yaml` 中通过 `${ENV_VAR}` 引用，环境变量通过系统环境注入。

### Q: 如何查看所有待审核内容？

**A**: 山海运行：
```python
from skills.content_review.scripts.api import list_pending_review
pending = list_pending_review(limit=50)
```

### Q: 反馈可以修改吗？

**A**: 可以。每轮审核都会生成新的反馈记录，通过 `ref:{content_id}` 标签关联。小山可以查看所有轮次的反馈。

### Q: 如何查看内容的审核历史？

**A**:
```python
from skills.content_review.scripts.api import get_feedback_history
history = get_feedback_history("mem_xxxxxxxxxx")
```

---

## 贡献与反馈

欢迎分享、引用与改进。

发现问题：欢迎提交 Issue
有改进建议：欢迎提交 Pull Request

## 相关链接

主站博客：https://kunpeng-ai.com
GitHub 组织：https://github.com/kunpeng-ai-research
OpenClaw 官方：https://openclaw.ai

## 维护与署名

维护者：鲲鹏AI探索局

## License

MIT
