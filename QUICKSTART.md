# Agent Memory System - 快速上手卡

## 一、安装（选一种）

### Windows
```bat
双击 install.bat
```

### Linux / macOS
```bash
chmod +x install.sh
./install.sh
```

---

## 二、基本命令

```bash
# 查看状态
python src/cli/memory_cli.py status

# 存储记忆（默认 private，不上传）
python src/cli/memory_cli.py store "这是一个本地记忆" --type general

# 分享经验到云端（用户触发）
python src/cli/memory_cli.py share-experience \
    --title "FastAPI性能优化" \
    --summary "uvicorn workers=4 最佳" \
    --notes "适用场景: 高并发API" \
    --tags fastapi,performance \
    "具体经验内容..."

# 查询云端他人经验
python src/cli/memory_cli.py cloud-query "FastAPI性能"

# 列出我的经验
python src/cli/memory_cli.py my-experiences

# 列出所有共享经验
python src/cli/memory_cli.py list-shared
```

---

## 三、OpenClaw 集成触发词

| 你说什么 | OpenClaw 做什么 |
|---------|----------------|
| `记住 xxx` | 存储到本地记忆 |
| `分享经验` | 分享经验到云端 |
| `谁有 xxx 经验` | 查询云端 |
| `查一下云端` | 列出共享经验 |

---

## 四、文件结构

```
agent-memory-system/
├── install.bat          # Windows 安装脚本
├── install.sh           # Linux/macOS 安装脚本
├── config.yaml          # 配置文件
├── README.md            # 完整文档
├── QUICKSTART.md        # 本文件
├── src/
│   ├── cli/
│   │   └── memory_cli.py   # CLI 主程序
│   └── adapters/
│       └── openclaw/        # OpenClaw 适配器
```

---

## 五、常见问题

**Q: 忘记密码了？**
A: 查看 config.yaml 或联系管理员

**Q: 连接失败？**
A: 检查网络是否可达 218.201.18.131:8999

**Q: 如何更新？**
A: 重新运行 install.sh 或手动 pull 最新代码
