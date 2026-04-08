# -*- coding: utf-8 -*-
"""
Test local file storage
"""

import os
import sys
from pathlib import Path

# Setup paths
base_dir = Path(r'C:\Users\openclaw-windows-2\.openclaw\workspace\agent-memory-system')
experiences_dir = base_dir / 'experiences'

# Create directory
experiences_dir.mkdir(exist_ok=True)

# Create sample MD file
sample_content = """# FastAPI性能优化最佳实践

## 摘要
使用 uvicorn workers=4 可以获得最佳性能。

## 测试数据
- workers=2: 1000 req/s
- workers=4: 1800 req/s (最佳)
- workers=8: 1600 req/s

## 结论
4 workers 是最佳选择。

## 备注
适用场景: 高并发API服务
注意事项: 根据CPU核心数调整

---
*来源: openclaw-sherlock | 领域: BACKEND | 重要性: 8/10*
*代码: EXP-BACKEND-FASTAPI-0001*
"""

# Save file
date_dir = experiences_dir / "2026-04"
date_dir.mkdir(exist_ok=True)

filepath = date_dir / "EXP-BACKEND-FASTAPI-0001.md"
filepath.write_text(sample_content, encoding='utf-8')

print("=" * 60)
print("  Local File Storage Test")
print("=" * 60)
print()
print(f"File saved to: {filepath}")
print(f"File exists: {filepath.exists()}")
print(f"File size: {filepath.stat().st_size} bytes")
print()
print("Content preview:")
print("-" * 40)
print(sample_content[:300])
print("-" * 40)
print()
print("Done!")
