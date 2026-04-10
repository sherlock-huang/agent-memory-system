---
name: voice-input
description: |
  语音输入技能 - 将语音转换为文字输入给 OpenClaw
  使用流程: 语音 → STT转写 → LLM校正 → 命令执行
  激活场景: 用户通过语音与 OpenClaw 交互时使用
---

# Voice Input Skill - 语音输入技能

让 OpenClaw 支持语音输入，实现"语音 → 转写 → 校正 → 执行"的完整交互流程。

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户语音   │ ──▶ │  录音模块    │ ──▶ │  Whisper    │ ──▶ │   LLM       │
│  (按住说话)  │     │  (pyaudio)  │     │   STT转写    │     │   语义校正   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                    │
                                                                    ▼
                                                            ┌─────────────┐
                                                            │  OpenClaw   │
                                                            │   执行命令   │
                                                            └─────────────┘
```

## 核心功能

### 1. 语音录制
- 支持按住空格键录音
- 自动结束或手动结束

### 2. 语音转写 (STT)
- 使用 `faster-whisper` 本地转写
- 支持中文、英文混合
- 模型可选: base/small/medium/large

### 3. 语义校正
- LLM 校正同音错字
- 还原专业术语
- 补全不完整指令

## 使用方式

### 方式 1: 命令行

```bash
# 进入项目目录
cd voice-agent

# 语音输入模式
python -m scripts.cli listen

# 直接校正文字
python -m scripts.cli correct "把昆仑的生日存到记忆"

# 测试模块
python -m scripts.cli test
```

### 方式 2: OpenClaw Skill 集成

```
用户: [按住空格键说话]
      ↓
OpenClaw Skill 接收录音
      ↓
调用 WhisperTranscriber 转写
      ↓
调用 TranscriptCorrector 校正
      ↓
执行命令并回复
```

## Python SDK

```python
from voice_agent.scripts import (
    AudioRecorder,
    WhisperTranscriber, 
    TranscriptCorrector
)

# 1. 录音
recorder = AudioRecorder()
audio, sr = recorder.record(duration=5)
recorder.close()

# 2. 转写
transcriber = WhisperTranscriber(model_size="base")
result = transcriber.transcribe(audio)
text = result["text"]

# 3. 校正
corrector = TranscriptCorrector()
corrected = corrector.correct(text)

# 4. 执行
print(f"最终命令: {corrected}")
```

## 安装依赖

```bash
# 核心依赖
pip install faster-whisper sounddevice numpy

# 可选：语音活动检测
pip install webrtcvad

# OpenAI SDK (用于 LLM 校正)
pip install openai
```

## 配置

通过环境变量配置：

```bash
# Whisper 模型
export WHISPER_MODEL=medium
export WHISPER_LANGUAGE=zh

# LLM API (用于校正)
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.minimax.chat/v1
export LLM_MODEL=MiniMax-Text-01
```

## 待实现

- [ ] 全局快捷键监听
- [ ] 语音活动检测 (VAD)
- [ ] 噪声抑制
- [ ] 离线模式
- [ ] 连续对话模式

## 项目结构

```
voice-agent/
├── SKILL.md
└── scripts/
    ├── __init__.py
    ├── config.py      # 配置管理
    ├── recorder.py    # 音频录制
    ├── transcriber.py # Whisper 转写
    ├── corrector.py   # LLM 校正
    └── cli.py         # 命令行入口
```
