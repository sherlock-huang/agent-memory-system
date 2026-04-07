# Agent Memory System - 详细设计文档

## 📂 项目路径

```
C:\Users\openclaw-windows-2\.openclaw\workspace\agent-memory-system
```

---

## 🎯 核心问题与解决方案

### 问题 1: 如何实现长期记忆？

**人类记忆机制 vs AI 解决方案:**

| 记忆类型 | 人类机制 | AI 解决方案 |
|---------|---------|------------|
| 瞬时记忆 | 感觉器官 | Context Window |
| 短时记忆 | 工作记忆 | Session Memory |
| 长期记忆 | 海马体 + 皮层 | Vector DB + KG |

**三层记忆架构:**

```
┌─────────────────────────────────────────────────────────────┐
│                    三层记忆架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Working Memory (工作记忆)                        │
│  位置: Agent 运行时内存                                    │
│  内容: 当前会话的所有交互                                   │
│  容量: Context Window 大小 (如 128K tokens)                │
│  生命周期: 会话结束即销毁                                   │
│                                                             │
│  Layer 2: Episodic Memory (情景记忆)                        │
│  位置: ChromaDB (向量数据库)                              │
│  内容: 会话摘要 + 关键事件 + 用户偏好                      │
│  生命周期: 持久化，直到手动删除                             │
│                                                             │
│  Layer 3: Semantic Memory (语义记忆)                        │
│  位置: SQLite (结构化) + 文件存储                          │
│  内容: 提取的知识、规则、经验总结                           │
│  生命周期: 持久化，定期更新                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 问题 2: 如何实现经验沉淀？

**人类经验积累流程:**

```
学习 → 经历 → 反思 → 总结 → 应用 → 迭代
```

**反思引擎 (Reflect Engine):**

```
触发条件 (满足任一即触发):
├── 每 N 条新记忆
├── 时间达到阈值 (如每天一次)
├── 任务复杂度高
└── 用户明确要求

反思流程:

1. 收集 (Collect)
   └── 从情景记忆中取出近期重要记忆

2. 反思 (Reflect)
   └── LLM 分析: "这些记忆告诉我们什么?"

3. 总结 (Summarize)
   └── 生成可复用的洞察 (Insights)

4. 存储 (Store)
   └── 存入语义记忆，形成经验
```

---

## 🧠 经典记忆架构参考

### 1. Generative Agents (2023) - 斯坦福

**论文:** Generative Agents: Interactive Simulacra of Human Behavior

**核心机制 - Memory Stream:**

```
Memory Stream (记忆流)
├── 重要性评分 (Importance)
├── 最近度评分 (Recency)
└── 相关性评分 (Relevance)
```

**反思机制:**
- 低层次记忆 → 高层次洞察
- 例如: "用户今天吃了炸鸡" → "用户喜欢吃炸鸡"

---

### 2. MemGPT (2024) - 层級记忆

**核心思想:** 像操作系统一样管理内存层级

```
┌─────────────────────────────────────┐
│         LLM (CPU 处理器)              │
├─────────────────────────────────────┤
│  Tier 1: 上下文窗口 (RAM)            │  ← 高速但有限
├─────────────────────────────────────┤
│  Tier 2: 外部向量存储 (SSD)          │  ← 容量大但慢
├─────────────────────────────────────┤
│  Tier 3: 归档存储 (云存储)            │  ← 长期存档
└─────────────────────────────────────┘
```

**核心操作:**
- memory_read() - 读取相关记忆到上下文
- memory_write() - 将新信息写入记忆
- memory_reclaim() - 清理不重要记忆

---

### 3. ZEP - 时序知识图谱

**核心思想:** 知识图谱 + 时间维度

```
时序知识图谱结构:

        用户偏好
           ↓
    [时间边: 2024-01]
           ↓
        具体行为
           ↓
    [时间边: 2024-06]  ← 随时间演变
           ↓
      变化后的偏好
```

**为什么需要时间维度?**
- 用户的偏好会变化
- 经验有过期时间
- 需要追踪演变过程

---

### 4. Mem0 - 生产级 Agent Memory

**设计哲学:**

```python
# Mem0 的记忆类型
class Memory:
    - episodic: 具体事件记忆
    - declarative: 事实知识
    - procedural: 技能/流程
```

---

## 🏗️ 我们的系统架构

### 记忆写入流程

```
用户输入
    ↓
┌─────────────────────────────────────────┐
│           Memory Manager                 │
├─────────────────────────────────────────┤
│  1. 分析 (Analyze)                       │
│     - 提取实体、关系、情感               │
│     - 评估重要性 (1-10分)                 │
│     - 分配记忆类型                        │
│                                          │
│  2. 路由 (Route)                         │
│     - importance > 8 → 情景记忆          │
│     - 需要长期保留 → 语义记忆            │
│     - 过程性知识 → 程序记忆              │
│                                          │
│  3. 存储 (Store)                         │
│     - 向量化存储                          │
│     - 建立关联                            │
│                                          │
│  4. 触发反思 (Check Reflect)            │
│     - 达到阈值? → 启动反思引擎          │
│                                          │
└─────────────────────────────────────────┘
```

### 记忆检索流程

```
用户查询
    ↓
┌─────────────────────────────────────────┐
│           Memory Manager                 │
├─────────────────────────────────────────┤
│  1. 理解查询 (Understand)                │
│     - 向量化查询内容                      │
│     - 识别查询意图                        │
│                                          │
│  2. 多路检索 (Multi-Retrieve)           │
│     ┌─────────┬─────────┬─────────┐    │
│     │向量相似 │  知识图  │ 精确匹配 │    │
│     │  搜索   │  关系   │  查询   │    │
│     └─────────┴─────────┴─────────┘    │
│              ↓                          │
│         结果融合                          │
│                                          │
│  3. 重新排序 (Rerank)                   │
│     - 综合相关性评分                      │
│     - 时间衰减因素                        │
│                                          │
│  4. 构建上下文 (Build Context)           │
│     - 格式化为自然语言                    │
│     - 注入到 Prompt                      │
│                                          │
└─────────────────────────────────────────┘
```

### 反思引擎流程

```
触发条件满足
    ↓
┌─────────────────────────────────────────┐
│           Reflect Engine                 │
├─────────────────────────────────────────┤
│  Phase 1: 收集 (Gather)                 │
│  - 获取近期情景记忆                       │
│  - 获取相关语义记忆                       │
│  - 获取用户偏好记录                       │
│                                          │
│  Phase 2: 分析 (Analyze)                 │
│  - LLM 分析共性模式                      │
│  - 识别矛盾点                            │
│  - 发现新趋势                            │
│                                          │
│  Phase 3: 总结 (Generalize)              │
│  输入: "用户每次问Python问题我都用xxx回答"│
│  输出: "用户的Python偏好: xxx"            │
│                                          │
│  Phase 4: 更新 (Update)                  │
│  - 更新语义记忆                           │
│  - 标记过期记忆                          │
│  - 记录反思元数据                         │
│                                          │
└─────────────────────────────────────────┘
```

---

## 📊 记忆数据结构设计

### 情景记忆 (Episodic Memory)

```typescript
interface EpisodicMemory {
  id: string;              // 唯一标识
  content: string;         // 原始内容
  summary: string;         // 自动摘要
  importance: number;       // 重要性 1-10
  createdAt: Date;         // 创建时间
  lastAccessedAt: Date;    // 最后访问
  tags: string[];          // 标签
  embedding: number[];      // 向量
  metadata: {
    sessionId: string;
    userId?: string;
    source: 'chat' | 'action' | 'reflection';
  };
}
```

### 语义记忆 (Semantic Memory)

```typescript
interface SemanticMemory {
  id: string;
  type: 'preference' | 'knowledge' | 'rule' | 'skill';
  content: string;         // 总结的知识
  confidence: number;       // 置信度
  validFrom: Date;
  validUntil?: Date;        // 可选过期时间
  evidence: string[];       // 支持证据
  contradictedBy?: string;  // 矛盾证据
  embedding: number[];
}
```

### 程序记忆 (Procedural Memory)

```typescript
interface ProceduralMemory {
  id: string;
  skillName: string;
  description: string;
  steps: string[];         // 执行步骤
  applicableScenarios: string[];
  successRate?: number;   // 统计成功率
  lastUsedAt: Date;
}
```

---

## 🔄 记忆生命周期

```
                    ┌──────────────┐
                    │   产生       │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  重要性评估   │ ←─── LLM 自动评分
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌────▼─────┐ ┌────▼──────┐
     │  高 (8-10)  │ │ 中 (4-7) │ │ 低 (1-3)  │
     └──────┬──────┘ └────┬─────┘ └────┬──────┘
            │              │              │
     ┌──────▼──────┐ ┌────▼─────┐ ┌────▼──────┐
     │ 情景记忆    │ │ 临时存储 │ │  丢弃/归档 │
     │ +反思触发  │ │          │ │           │
     └────────────┘ └──────────┘ └───────────┘
```

---

## 🎯 经验沉淀机制

### 从"数据"到"智慧"的演进

```
数据 (Data)
   ↓ 观察
信息 (Information)
   ↓ 理解
知识 (Knowledge)
   ↓ 实践
智慧 (Wisdom)
```

### 我们的实现:

```python
# Level 1: 原始记录
store("用户问如何Python排序")

# Level 2: 经验总结 (通过反思)
# 用户偏好: Python
# 任务类型: 代码问题
# 回答策略: 直接给代码+解释

# Level 3: 知识固化 (定期整合)
# 规则: 处理用户代码问题时，优先用Python示例

# Level 4: 主动应用
# 检测到类似场景时，自动提供帮助
```

---

## 🔮 未来扩展

### Phase 2: 知识图谱

```
用户 ←has_preference→ Python
         ↓
    ←related_to→
         ↓
     算法问题
```

### Phase 3: 主动记忆

- 定期回顾旧记忆
- 发现遗忘点主动补充
- 跨用户知识迁移

---

## 📚 参考资料

1. [Generative Agents](https://arxiv.org/abs/2304.03442) - 斯坦福 2023
2. [MemGPT](https://memgpt.ai/) - 层級记忆管理
3. [ZEP](https://arxiv.org/abs/2403.00112) - 时序知识图谱
4. [Mem0](https://github.com/mem0ai/mem0) - 生产级 Agent Memory
5. [GraphRAG](https://www.microsoft.com/en-us/research/project/graphrag/) - 微软图增强RAG
