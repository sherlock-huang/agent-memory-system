---
name: content-creation
description: |
  内容创作技能 - 小山生成内容的两 Agent 协作工作流
  激活场景: 用户提到"生成内容"、"写小红书"、"写公众号"、"生成文案"、"提交审核"
  当需要扮演内容创作者角色时使用此技能
---

# Content Creation Skill - 内容创作技能

让 AI Agent 能够进行内容创作，并将内容提交到审核流程。

## 功能概述

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 创作内容 | 根据主题生成完整内容 | "生成内容"、"写小红书"、"创作" |
| 提交审核 | 将内容提交给山海审核 | "提交审核"、"送审" |
| 查看审核状态 | 查看当前内容的审核进度 | "审核状态"、"查看进度" |
| 查看反馈 | 查看山海给出的审核反馈 | "查看反馈"、"审核意见" |
| 修改内容 | 根据反馈修改内容 | "修改内容"、"修订" |

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

## 工作流

### Step 1: 创作内容

```
用户: 帮我写一篇关于"AI大模型发展趋势"的小红书

Agent:
1. 分析主题，确定内容方向
2. 生成完整内容（标题、正文、封面文案、话题标签）
3. 存入本地草稿（不提交审核）
4. 展示给用户确认
5. 等待用户修改指令
```

### Step 2: 提交审核

```
用户: 提交审核

Agent:
1. 调用 submit_for_review(content_id) 提交内容
2. 内容状态变为 content:pending_review
3. 自动通知山海（有新的待审核内容）
```

### Step 3: 查看反馈

```
用户: 查看审核反馈

Agent:
1. 调用 get_feedback_history(content_id) 获取反馈
2. 展示评分、问题、建议
3. 询问用户是否修改
```

### Step 4: 修改内容

```
用户: 根据反馈修改

Agent:
1. 分析反馈意见
2. 修改内容
3. 重新提交审核
```

---

## API 参考

### submit_for_review(content_id, platform, title, content, cover_text, hashtags, author_id="xiao_shan")

提交内容进入审核流程。

**参数**:
- `content_id`: str - 内容 ID（来自 store_content 返回）
- `platform`: str - 平台（小红书/抖音/公众号/b站/博客）
- `title`: str - 标题
- `content`: str - 正文
- `cover_text`: str - 封面文案
- `hashtags`: list - 话题标签列表
- `author_id`: str - 作者 ID（默认 xiao_shan）

**返回**: `dict` - 提交结果

**示例**:
```python
from skills.content_creation.scripts.api import submit_for_review

result = submit_for_review(
    content_id="mem_xxxxxxxxxx",
    platform="小红书",
    title="AI大模型发展的5个趋势",
    content="...",
    cover_text="2024年AI会变成什么样？",
    hashtags=["AI", "人工智能", "科技趋势"],
    author_id="xiao_shan"
)
print(f"已提交审核: {result['id']}")
```

### store_content(platform, title, content, cover_text, hashtags, author_id="xiao_shan")

存储内容到草稿。

**参数**:
- `platform`: str - 平台
- `title`: str - 标题
- `content`: str - 正文
- `cover_text`: str - 封面文案
- `hashtags`: list - 话题标签
- `author_id`: str - 作者 ID

**返回**: `dict` - 包含 id 和 content 对象

### get_content_status(content_id)

获取内容审核状态。

**参数**: `content_id` - 内容 ID

**返回**: `dict` - 状态信息

### list_my_drafts(author_id="xiao_shan", limit=10)

列出当前作者的所有草稿。

**参数**:
- `author_id`: str - 作者 ID
- `limit`: int - 返回数量

**返回**: 草稿列表

---

## 内容格式

### 小红书内容结构

```json
{
  "platform": "小红书",
  "title": "标题（最多20字）",
  "content": "正文（300-500字）",
  "cover_text": "封面文案（5-10字）",
  "hashtags": ["#话题1", "#话题2"],
  "author": "作者名"
}
```

### 公众号内容结构

```json
{
  "platform": "公众号",
  "title": "标题",
  "content": "正文",
  "cover_image": "封面图建议",
  "summary": "摘要（可选）",
  "author": "作者名"
}
```

---

## 注意事项

1. **内容必须完整**: 提交前确认标题、正文、封面文案、标签都有
2. **标签要适配平台**: 
   - 小红书: #话题 格式，至少3个
   - 公众号: 关键词，最多5个
   - B站: #话题 格式，至少2个
3. **提交审核后不能再修改**: 如需修改，先撤回或等反馈后重新提交
4. **存储敏感信息脱敏**: 不要在内容中包含真实姓名、电话等
