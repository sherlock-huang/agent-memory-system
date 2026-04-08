# Agent Memory System - 云端经验共享系统

跨 Agent 记忆共享系统，支持将经验上传到云端 MinIO 存储，其他 Agent 可下载学习。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     云端服务器 (218.201.18.133)                  │
│  ┌───────────────────┐    ┌─────────────────────────────────┐  │
│  │   MinIO (S3)      │    │         MySQL                    │  │
│  │   端口: 9002       │    │         端口: 8999               │  │
│  │   Bucket: openclaw │    │   数据库: agent_memory           │  │
│  │   存储 MD 文件      │    │   存储经验元数据                 │  │
│  └───────────────────┘    └─────────────────────────────────┘  │
│           ↑                            ↑                         │
│           │         元数据 + 文件路径    │                         │
│           └────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                    Agent 请求 (S3 API + MySQL)
```

## 快速安装

### 第一步：服务器部署（云端管理人员执行，一次性）

```bash
# 连接到云服务器
ssh root@218.201.18.133

# 部署 MinIO（如果尚未部署）
docker run -d --name minio --restart=always \
  -p 9002:9000 -p 8080:9001 \
  -v /data/minio:/data \
  -e 'MINIO_ROOT_USER=admin' \
  -e 'MINIO_ROOT_PASSWORD=Minio12345678' \
  minio/minio:latest server /data --console-address ':9001'

# 创建 bucket
docker run --rm --network host -v /tmp:/tmp minio/mc \
  sh -c 'mc alias set myminio http://127.0.0.1:9002 admin Minio12345678 && mc mb myminio/openclaw'
```

### 第二步：客户端安装（每台 OpenClaw 机器执行）

```bash
# 克隆项目
git clone <仓库地址> agent-memory-system
cd agent-memory-system

# Windows 安装
install.bat

# Linux/macOS 安装
chmod +x install.sh && ./install.sh
```

### 第三步：配置

编辑 `config.yaml`：

```yaml
# MinIO 云端存储
minio:
  endpoint: "218.201.18.133:9002"
  access_key: "admin"
  secret_key: "Minio12345678"
  bucket: "openclaw"
  region: "cn-east-1"

# MySQL 数据库
database:
  type: mysql
  host: "218.201.18.133"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "你的密码"
  charset: "utf8mb4"

source: "cli"
agent_id: null

search:
  default_limit: 10
  max_limit: 100

log_level: "INFO"
```

### 第四步：初始化数据库

```bash
# 创建数据库表
mysql -h 218.201.18.133 -P 8999 -u root1 -p agent_memory < scripts/init_mysql.sql
mysql -h 218.201.18.133 -P 8999 -u root1 -p agent_memory < scripts/init_experiences.sql
```

## 使用方法

### 查看状态
```bash
python src/cli/memory_cli.py status
```

### 存储本地记忆（不上传）
```bash
python src/cli/memory_cli.py store "这是一个本地记忆" --type general
```

### 分享经验到云端（用户触发）
```bash
python src/cli/memory_cli.py exp-create \
    --title "MinIO部署最佳实践" \
    --summary "S3兼容存储，Agent友好" \
    --tags minio,storage,s3 \
    --domain DEVOPS \
    --importance 8 \
    --content "# MinIO部署经验

## 环境
CentOS 7, Docker

## 步骤
1. 部署 MinIO 容器
2. 配置 Nginx 反向代理
3. 创建 bucket

## 注意事项
端口需在安全组开放"
```

### 查询云端经验
```bash
python src/cli/memory_cli.py cloud-query "MinIO部署"
```

### 下载并学习经验
```bash
# 获取经验详情（包含文件路径）
python src/cli/memory_cli.py exp-get EXP-DEVOPS-MINIO-0001

# 下载 MD 文件到本地
python src/cli/memory_cli.py exp-download EXP-DEVOPS-MINIO-0001 --output ./learned/
```

### 列出所有云端经验
```bash
python src/cli/memory_cli.py exp-list
```

## 经验代码规则

每个经验有唯一代码，格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

| 部分 | 说明 | 示例 |
|------|------|------|
| `EXP` | 固定前缀 | EXP |
| `{DOMAIN}` | 领域 | BACKEND / DEVOPS / AI |
| `{TAG}` | 主要标签 | MINIO / DOCKER / FASTAPI |
| `{SEQ:4}` | 序号 | 0001 |

### 领域代码

| 代码 | 领域 |
|------|------|
| `BACKEND` | 后端 |
| `FRONTEND` | 前端 |
| `DEVOPS` | 运维 |
| `AI` | 人工智能 |
| `DATABASE` | 数据库 |
| `GENERAL` | 通用 |

## OpenClaw 触发词

| 用户输入 | OpenClaw 动作 |
|---------|--------------|
| `记住xxx` | 存储到本地记忆 |
| `分享经验` | 分享经验到云端（MinIO + MySQL） |
| `谁有xxx经验` | 查询云端经验 |
| `借鉴云端经验` | 下载并学习云端经验 |

## 项目结构

```
agent-memory-system/
├── src/
│   ├── core/                 # 核心模块
│   │   ├── config.py         # 配置管理
│   │   ├── models.py         # 数据模型
│   │   ├── database.py        # MySQL 连接
│   │   ├── minio_client.py   # MinIO 客户端 ⭐
│   │   ├── file_storage.py   # 文件存储
│   │   └── search.py          # 搜索
│   ├── cli/
│   │   └── memory_cli.py     # CLI 主程序
│   └── adapters/             # Agent 适配器
│       └── openclaw/         # OpenClaw 专用
├── scripts/
│   ├── init_mysql.sql        # MySQL 初始化
│   └── init_experiences.sql  # 经验表
├── skills/
│   └── minio-storage/        # MinIO Skill ⭐
├── config.yaml.example       # 配置示例
├── install.bat / install.sh   # 安装脚本
└── README.md
```

## 云端服务信息

### MinIO (S3 兼容存储)
| 配置项 | 值 |
|--------|-----|
| **API 地址** | `http://218.201.18.133:9002` |
| **Console** | `http://218.201.18.133:8080` |
| **Bucket** | `openclaw` |
| **Access Key** | `admin` |
| **Secret Key** | `Minio12345678` |

### MySQL (元数据)
| 配置项 | 值 |
|--------|-----|
| **地址** | `218.201.18.133:8999` |
| **数据库** | `agent_memory` |
| **用户名** | `root1` |

## 文件命名规范

### 云端经验文件
```
experiences/
├── 2026-04/
│   ├── EXP-DEVOPS-MINIO-0001.md
│   ├── EXP-BACKEND-FASTAPI-0001.md
│   └── ...
```

### MD 文件格式
```markdown
# 经验标题

## 摘要
一句话概括

## 标签
#tag1 #tag2

## 正文
详细经验内容...

## 元数据
*代码: EXP-DEVOPS-MINIO-0001*
*领域: DEVOPS*
*重要性: 8/10*
```

## 常见问题

### Q: MinIO 连接失败
A: 检查端口 9002 是否在安全组开放

### Q: Console 打不开
A: 检查端口 8080 是否在安全组开放，或访问 http://218.201.18.133:8080

### Q: 上传失败
A: 确认 MinIO bucket `openclaw` 已创建，权限正确

### Q: 数据库连接失败
A: 检查 MySQL 端口 8999 是否开放，密码是否正确
