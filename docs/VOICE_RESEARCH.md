# Voice Interaction Project - 技术调研

## 项目目标

实现语音输入 → 转写 → 校正 → 执行 的完整交互流程，让用户可以通过语音指挥 OpenClaw。

## 核心流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  语音输入    │ ──▶ │  语音转写    │ ──▶ │   语义校正   │ ──▶ │  命令执行   │
│ (Push-to-Talk)│     │   (STT)     │     │  (LLM)      │     │ (OpenClaw) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## 技术选型

### 1. 语音转写 (STT)

#### 方案 A: faster-whisper (本地，推荐)

| 优点 | 缺点 |
|------|------|
| 本地运行，隐私保护 | 首次下载模型较大 |
| 支持中文，效果好 | 需要 GPU 加速（可选） |
| 无需 API 费用 | |

**安装:**
```bash
pip install faster-whisper
```

**模型选择:**
| 模型 | 大小 | 中文效果 | 速度 |
|------|------|----------|------|
| base | ~140MB | 一般 | 快 |
| medium | ~1GB | 较好 | 中 |
| large-v3 | ~3GB | 最好 | 慢 |

**中文推荐:** `medium` 或 `large-v3` 模型

#### 方案 B: OpenAI Whisper API

| 优点 | 缺点 |
|------|------|
| 效果好 | 需要 API Key |
| 无需本地算力 | 有费用 |
| | 网络延迟 |

#### 方案 C: 讯飞/百度/腾讯 ASR (中文云端)

| 优点 | 缺点 |
|------|------|
| 中文优化好 | 需要账号 |
| 响应快 | 有费用 |
| | 隐私顾虑 |

**推荐:** 优先使用 **faster-whisper + medium 模型**（本地优先，保护隐私）

### 2. 语义校正 (LLM Correction)

转写后可能存在：
- 同音错字（"昆仑" → "昆虫"）
- 专业术语错误（"Python" → "派森"）
- 指令不完整

**校正 prompt 示例:**
```python
CORRECTION_PROMPT = """你是一个语音输入校正助手。用户通过语音输入了一段文字，可能存在转写错误。

请进行以下校正：
1. 修正明显的同音错字
2. 还原专业术语（代码、技术名词等）
3. 补全不完整的指令
4. 保持原意不变

只输出校正后的文字，不要解释。

用户输入: {transcript}

校正后:"""
```

### 3. 语音输入方式

#### Push-to-Talk (推荐)
- 按住空格键或自定义按键录音
- 松开自动发送
- 简单可靠，隐私友好

#### 快捷键触发
- 监听全局快捷键（如 `Ctrl+Shift+V`）
- 触发后开始录音

### 4. 音频录制

**Windows 方案:**
```python
# 方案1: pyaudio (需要安装 portaudio)
pip install pyaudio

# 方案2: sounddevice (更现代)
pip install sounddevice numpy

# 方案3: 直接用 Whisper 的输入
```

**推荐:** `sounddevice + numpy` 组合

## 项目结构设计

```
voice-agent/
├── voice_agent/
│   ├── __init__.py
│   ├── recorder.py       # 音频录制
│   ├── transcriber.py    # STT 转写
│   ├── corrector.py      # LLM 校正
│   ├── config.py         # 配置
│   └── cli.py            # 命令行入口
├── skills/
│   └── voice-input/
│       ├── SKILL.md
│       └── scripts/
├── requirements.txt
└── README.md
```

## 功能模块

### recorder.py - 音频录制

```python
class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
    
    def record(self, duration=None):
        """
        录制音频
        
        Args:
            duration: 录制时长(秒)，None表示手动停止
        
        Returns:
            numpy array: 音频数据
        """
        
    def record_until_silence(self, silence_threshold=0.01, max_duration=30):
        """
        录制到静音自动停止
        """
```

### transcriber.py - 语音转写

```python
from faster_whisper import WhisperModel

class WhisperTranscriber:
    def __init__(self, model_size="medium", device="auto"):
        # device: "cpu", "cuda", "auto"
        
    def transcribe(self, audio_array, language="zh") -> str:
        """
        转写音频为文字
        
        Args:
            audio_array: numpy 音频数据
            language: 语言代码
        
        Returns:
            str: 转写文字
        """
```

### corrector.py - LLM 校正

```python
class TranscriptCorrector:
    def __init__(self, api_key=None, base_url=None):
        # 支持 OpenAI 兼容 API
    
    def correct(self, transcript: str) -> str:
        """
        校正转写文字
        
        Args:
            transcript: 原始转写
        
        Returns:
            str: 校正后文字
        """
```

## 交互流程

### 方式 1: 命令行模式

```bash
# 按空格开始录音，松开停止
python -m voice_agent.cli listen

# 指定时长录音
python -m voice_agent.cli listen --duration 5

# 测试模式（直接输入文字）
python -m voice_agent.cli correct "把昆仑的生日存到记忆"
```

### 方式 2: OpenClaw Skill 集成

```
用户: [长按空格键说话]
      ↓
OpenClaw Skill 接收音频
      ↓
faster-whisper 转写
      ↓
LLM 校正
      ↓
执行命令并回复
```

## 安装依赖

```bash
pip install faster-whisper sounddevice numpy
```

**Windows 可能需要额外安装:**
```bash
# 安装 PortAudio (用于 sounddevice)
# 下载 portaudio-19.6.0.0-bin.zip
# 解压到 Python 目录
```

## 待解决问题

1. [ ] Windows 音频录制权限和库依赖
2. [ ] 模型下载和缓存管理
3. [ ] 噪声抑制和回声消除
4. [ ] 离线模式支持
5. [ ] 多语言混合处理

## 下一步行动

1. 先在 Windows 上安装并测试 `sounddevice` + `faster-whisper`
2. 实现基本的录音和转写功能
3. 添加 LLM 校正层
4. 集成到 OpenClaw Skill

## 参考资料

- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Whisper 中文模型对比](https://huggingface.co/blog/zh/whisper)
- [sounddevice](https://python-sounddevice.readthedocs.io/)
