---
name: content-review
description: |
  内容创作审核技能 - 小山生成、山海审核的两 Agent 协作工作流
  激活场景: 用户提到"审核内容"、"查看待审核"、"给反馈"、"评分"
  当需要扮演审核者角色时使用此技能
---

# Content Review Skill - 内容审核技能

让 AI Agent 能够进行内容质量审核，支持评分、反馈、多轮修订的协作流程。

## 功能概述

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 列出待审核 | 列出所有待审核内容 | "待审核"、"查看审核队列" |
| 获取内容 | 获取单条内容详情 | "获取内容 {ID}"、"查看 {标题}" |
| 审核评分 | 对内容进行质量评分 | "审核"、"评分" |
| 写入反馈 | 提交审核反馈 | "写入反馈"、"提交审核意见" |
| 查看反馈 | 查看某条内容的反馈历史 | "查看反馈" |

---

## 核心概念

### 状态标签

| 状态 | 标签 | 说明 |
|------|------|------|
| 草稿 | `content:draft` | 未提交审核 |
| 待审核 | `content:pending_review` | 等待审核 |
| 需修改 | `content:needs_revision` | 需要修改 |
| 审核通过 | `content:approved` | 可以发布 |
| 已发布 | `content:published` | 已发布 |

### 平台标签

| 平台 | 标签 |
|------|------|
| 小红书 | `platform:小红书` |
| 抖音 | `platform:抖音` |
| 公众号 | `platform:公众号` |
| B站 | `platform:b站` |
| 博客 | `platform:博客` |

---

## 使用方法

### Step 1: 列出待审核内容

```
用户: 有哪些内容待审核？

Agent:
1. 调用 list_pending_review() 获取待审核列表
2. 格式化输出：ID、标题、平台、作者、提交时间
3. 询问用户选择要审核的内容
```

### Step 2: 获取内容详情

```
用户: 查看 ID 为 xxx 的内容

Agent:
1. 调用 get_content_by_id(id) 获取详情
2. 解析 content 字段的 JSON
3. 展示完整内容供审核
```

### Step 3: 进行审核评分

```
Agent 审查内容后:
1. 根据以下维度评分（每项 0-10）：
   - title: 标题吸引力 (权重 20%)
   - content: 内容质量 (权重 40%)
   - cover: 封面/配图 (权重 20%)
   - hashtags: 标签选择 (权重 10%)
   - platform_fit: 平台适配度 (权重 10%)

2. 综合分 = 加权平均

3. 审核结论：
   - ≥7.0: approved（通过）
   - 4.0-6.9: needs_revision（需修改）
   - <4.0: rejected（需重写）
```

### Step 4: 写入审核反馈

```
Agent:
1. 调用 submit_feedback(content_id, scores, issues, summary)
2. 创建反馈经验，包含：
   - 各项评分
   - 具体问题列表（section, issue, suggestion）
   - 优点列表
   - 总体评价
3. 更新原内容状态标签
```

---

## API 参考

### list_pending_review(limit=10)

列出待审核内容。

**返回**: `List[Memory]` - 待审核的记忆列表

**示例**:
```python
from skills.content_review.api import list_pending_review

pending = list_pending_review(limit=10)
for item in pending:
    print(f"ID: {item.id}")
    print(f"标题: {item.share_title}")
    print(f"平台: {[t for t in item.tags if t.startswith('platform:')]}")
    print(f"作者: {item.source_agent}")
    print()
```

### get_content_by_id(content_id)

获取内容详情。

**参数**: `content_id` - 内容 ID

**返回**: `dict` - 解析后的内容 JSON

**示例**:
```python
from skills.content_review.api import get_content_by_id

content = get_content_by_id("mem_xxxxxxxxxx")
print(f"平台: {content['platform']}")
print(f"标题: {content['title']}")
print(f"正文: {content['content']}")
print(f"封面: {content['cover_text']}")
print(f"标签: {content['hashtags']}")
```

### submit_feedback(content_id, scores, issues, summary, strengths=None, approved=None)

提交审核反馈。

**参数**:
- `content_id`: str - 原内容 ID
- `scores`: dict - 各项评分
- `issues`: list - 问题列表 `[{section, issue, suggestion}]`
- `summary`: str - 总体评价
- `strengths`: list - 优点列表（可选）
- `approved`: bool - 是否通过（可选，根据综合分自动判断）

**返回**: `Memory` - 创建的反馈记忆

**示例**:
```python
from skills.content_review.api import submit_feedback

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
    approved=False
)

print(f"反馈已创建: {feedback.id}")
```

### get_feedback_history(content_id)

获取某内容的反馈历史。

**参数**: `content_id` - 原内容 ID

**返回**: `List[Memory]` - 反馈列表（按时间倒序）

---

## 评分标准参考

### 综合分计算

```
综合分 = title×0.2 + content×0.4 + cover×0.2 + hashtags×0.1 + platform_fit×0.1
```

### 审核结论

| 综合分 | 结论 | 操作 |
|--------|------|------|
| ≥7.0 | ✅ 通过 | 更新状态为 `approved` |
| 4.0-6.9 | ⚠️ 需修改 | 更新状态为 `needs_revision` |
| <4.0 | ❌ 需重写 | 更新状态为 `draft`，通知作者 |

### 各维度参考标准

| 分值 | 标准 |
|------|------|
| 9-10 | 极佳，超越预期 |
| 7-8 | 良好，符合要求 |
| 5-6 | 一般，有改进空间 |
| 3-4 | 较差，需要大改 |
| 1-2 | 极差，不可用 |

---

## 注意事项

1. **反馈必须具体**: 每条 issue 需包含具体问题和明确修改建议
2. **评分必须有依据**: 每项评分都要有具体理由
3. **优点也要提**: 肯定做得好的地方，激励作者
4. **区分平台特性**: 
   - 小红书：重视封面文案、话题标签
   - 公众号：重视标题、内容深度
   - B站：重视开头几秒、互动引导
5. **维护反馈链**: 每次反馈都关联原内容 ID，形成可追溯的修订历史
