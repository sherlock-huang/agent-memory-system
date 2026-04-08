---
name: minio-storage
description: 云端文件存储技能 - 使用 MinIO/S3 API 上传和下载经验文件
---

# MinIO 云端存储技能

用于 Agent 间共享经验文件的云端存储。

## 连接信息

| 配置项 | 值 |
|--------|-----|
| **S3 API** | `http://218.201.18.133:9002` |
| **Console** | `http://218.201.18.133:8080` |
| **Bucket** | `openclaw` |
| **Access Key** | `admin` |
| **Secret Key** | `Minio12345678` |

## Python SDK 使用

```python
from src.core.minio_client import MinIOClient

client = MinIOClient()

# 上传经验文件
client.upload_experience(
    local_path="./experiences/EXP-DEVOPS-MINIO-0001.md",
    remote_key="experiences/2026-04/EXP-DEVOPS-MINIO-0001.md"
)

# 列出云端经验
files = client.list_experiences("experiences/")
for f in files:
    print(f"{f['key']} - {f['size']} bytes")

# 下载经验文件
client.download_experience(
    remote_key="experiences/2026-04/EXP-DEVOPS-MINIO-0001.md",
    local_path="./learned/EXP-DEVOPS-MINIO-0001.md"
)
```

## CLI 命令

```bash
# 测试连接
python src/core/minio_client.py test

# 上传文件
python src/core/minio_client.py upload --file ./test.md --key experiences/test.md

# 下载文件
python src/core/minio_client.py download --key experiences/test.md --output ./test.md

# 列出文件
python src/core/minio_client.py list

# 删除文件
python src/core/minio_client.py delete --key experiences/test.md
```

## Node.js SDK

```javascript
const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');

const s3 = new S3Client({
  endpoint: 'http://218.201.18.133:9002',
  region: 'cn-east-1',
  credentials: {
    accessKeyId: 'admin',
    secretAccessKey: 'Minio12345678',
  },
  forcePathStyle: true,
});

// 上传
await s3.send(new PutObjectCommand({
  Bucket: 'openclaw',
  Key: 'experiences/2026-04/EXP-DEVOPS-MINIO-0001.md',
  Body: Buffer.from(content),
}));

// 下载
const response = await s3.send(new GetObjectCommand({
  Bucket: 'openclaw',
  Key: 'experiences/2026-04/EXP-DEVOPS-MINIO-0001.md',
}));
```

## 经验文件路径规范

```
experiences/
├── 2026-04/
│   ├── EXP-DEVOPS-MINIO-0001.md
│   ├── EXP-BACKEND-FASTAPI-0001.md
│   └── ...
```
