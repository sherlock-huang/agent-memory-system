---
name: minio-storage
description: 云端文件存储技能 - 使用 MinIO/S3 API 上传和下载经验文件，元数据写入 MySQL
---

# MinIO 云端存储技能

用于 Agent 间共享经验文件的云端存储。

## 重要：完整的经验存储流程

**必须同时完成两个操作，缺一不可：**

### 1. 上传经验文件到 MinIO (S3)

```python
from src.core.minio_client import MinIOClient

minio_client = MinIOClient()

# 上传 MD 文件到 S3
minio_client.upload_experience(
    local_path="./experiences/EXP-DEVOPS-MINIO-0001.md",
    remote_key="experiences/2026-04/EXP-DEVOPS-MINIO-0001.md"
)
```

### 2. 写入元数据到 MySQL

```python
from src.core.database import Database

db = Database()
db.execute(
    "INSERT INTO experiences (code, title, summary, tags, domain, importance, author_id, file_key, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
    (code, title, summary, tags, domain, importance, author_id, file_key, int(time.time()))
)
```

---

## 连接信息

| 配置项 | 值 |
|--------|-----|
| **S3 API** | `http://YOUR_SERVER_IP:8010` |
| **Console** | `http://YOUR_SERVER_IP:8080` |
| **MySQL** | `YOUR_SERVER_IP:8999` |
| **Bucket** | `openclaw` |
| **Access Key** | `YOUR_ACCESS_KEY` |
| **Secret Key** | `YOUR_SECRET_KEY` |

---

## 数据库表结构

### experiences 表（经验元数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT AUTO_INCREMENT | 主键 |
| `code` | VARCHAR(50) | 经验代码，如 `EXP-DEVOPS-MINIO-0001` |
| `title` | VARCHAR(200) | 经验标题 |
| `summary` | TEXT | 一句话摘要 |
| `tags` | VARCHAR(500) | 标签，逗号分隔 |
| `domain` | VARCHAR(50) | 领域，如 DEVOPS, BACKEND |
| `importance` | INT | 重要性 1-10 |
| `author_id` | VARCHAR(100) | 作者 ID |
| `file_key` | VARCHAR(500) | S3 文件路径，如 `experiences/2026-04/EXP-DEVOPS-MINIO-0001.md` |
| `created_at` | BIGINT | 创建时间戳 |

---

## 完整经验上传流程

```python
import time
from src.core.minio_client import MinIOClient
from src.core.database import Database

def upload_experience(local_md_path, code, title, summary, tags, domain, importance, author_id):
    # Step 1: 上传到 S3
    minio = MinIOClient()
    file_key = f"experiences/{time.strftime('%Y-%m')}/{code}.md"
    minio.upload_experience(local_md_path, file_key)
    
    # Step 2: 写入 MySQL 元数据
    db = Database()
    db.execute(
        """INSERT INTO experiences 
           (code, title, summary, tags, domain, importance, author_id, file_key, created_at) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (code, title, summary, tags, domain, importance, author_id, file_key, int(time.time()))
    
    print(f"✓ 经验 {code} 已上传到云端")
```

---

## 完整经验获取流程

```python
from src.core.database import Database
from src.core.minio_client import MinIOClient

def download_experience(code, output_dir="./learned"):
    # Step 1: 从 MySQL 查询文件位置
    db = Database()
    result = db.query(
        "SELECT file_key, title FROM experiences WHERE code = %s",
        (code,))
    
    if not result:
        print(f"✗ 经验 {code} 不存在")
        return
    
    file_key = result[0]['file_key']
    
    # Step 2: 从 S3 下载文件
    minio = MinIOClient()
    local_path = f"{output_dir}/{code}.md"
    minio.download_experience(file_key, local_path)
    
    print(f"✓ 经验 {code} 已下载到 {local_path}")
```

---

## 查询云端经验

```python
from src.core.database import Database

def search_experiences(keyword, domain=None, limit=10):
    db = Database()
    
    if domain:
        result = db.query(
            "SELECT code, title, summary, tags, domain, importance, author_id, created_at "
            "FROM experiences WHERE domain = %s AND (title LIKE %s OR summary LIKE %s) "
            "ORDER BY importance DESC, created_at DESC LIMIT %s",
            (domain, f"%{keyword}%", f"%{keyword}%", limit))
    else:
        result = db.query(
            "SELECT code, title, summary, tags, domain, importance, author_id, created_at "
            "FROM experiences WHERE title LIKE %s OR summary LIKE %s OR tags LIKE %s "
            "ORDER BY importance DESC, created_at DESC LIMIT %s",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
    
    return result
```

---

## 经验代码规则

格式：`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

| 部分 | 说明 | 示例 |
|------|------|------|
| `EXP` | 固定前缀 | EXP |
| `{DOMAIN}` | 领域 | DEVOPS / BACKEND / AI |
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

---

## Python SDK

```python
from src.core.minio_client import MinIOClient
from src.core.database import Database

# S3 操作
minio = MinIOClient()
minio.upload_experience(local_path, remote_key)
minio.download_experience(remote_key, local_path)
files = minio.list_experiences(prefix="experiences/")

# MySQL 操作
db = Database()
result = db.query("SELECT * FROM experiences WHERE code = %s", (code,))
db.execute("INSERT INTO experiences (...) VALUES (...)", data)
```

## CLI 命令

```bash
# 测试 S3 连接
python src/core/minio_client.py test

# 上传文件
python src/core/minio_client.py upload --file ./test.md --key experiences/test.md

# 下载文件
python src/core/minio_client.py download --key experiences/test.md --output ./test.md
```

## Node.js SDK

```javascript
const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');

const s3 = new S3Client({
  endpoint: 'http://YOUR_SERVER_IP:8010',
  region: 'cn-east-1',
  credentials: {
    accessKeyId: 'YOUR_ACCESS_KEY',
    secretAccessKey: 'YOUR_SECRET_KEY',
  },
  forcePathStyle: true,
});
```

## 经验文件路径规范

```
experiences/
├── 2026-04/
│   ├── EXP-DEVOPS-MINIO-0001.md
│   ├── EXP-BACKEND-FASTAPI-0001.md
│   └── ...
```
