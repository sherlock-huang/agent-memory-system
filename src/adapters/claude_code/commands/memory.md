# Memory Commands

## 存储记忆
`/memory store <content> [--type project|preference|knowledge|team] [--tags tag1,tag2] [--importance 1-10]`

存储重要信息到跨 Agent 共享记忆库。

**示例：**
```
/memory store 项目使用 FastAPI 框架 --type project --tags python,fastapi
/memory store 用户偏好简洁回复 --type preference --tags communication
```

## 搜索记忆
`/memory search <query> [--type type] [--limit 10]`

搜索共享记忆库中的相关记忆。

**示例：**
```
/memory search python
/memory search 编码规范 --type project
```

## 列出记忆
`/memory list [--type type] [--limit 50]`

列出记忆库中的记忆。

**示例：**
```
/memory list --type project
/memory list --limit 20
```

## 获取记忆
`/memory get <memory-id>`

获取单条记忆的详情。

**示例：**
```
/memory get mem_abc123
```

## 删除记忆
`/memory delete <memory-id> [--hard]`

删除记忆。`--hard` 表示永久删除。

## 查看状态
`/memory status`

查看记忆库状态和统计。

## 列出标签
`/memory tags`

列出所有使用的标签。

## 导出/导入
`/memory export [--file backup.json]`
`/memory import <file>`

备份和恢复记忆。

---

## 记忆类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| `project` | 项目相关 | 项目规范、技术栈 |
| `preference` | 用户偏好 | 沟通风格、技术选择 |
| `knowledge` | 知识积累 | 解决方案、经验 |
| `team` | 团队共享 | 团队规范、流程 |
| `general` | 通用 | 其他 |

## 可见性

| 可见性 | 说明 |
|--------|------|
| `private` | 仅自己可见 |
| `shared` | 同项目可见 |
| `global` | 所有 Agent 可见 |

---

**注意：** 记忆存储在云端 MySQL 数据库，多个 Agent 共享。
