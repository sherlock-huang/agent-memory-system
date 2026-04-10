# -*- coding: utf-8 -*-
"""
Voice Agent - 语音转写模块
使用 faster-whisper 进行本地 STT
"""

import os
import numpy as np
from typing import Optional, List, Dict, Any

from .config import get_config


class WhisperTranscriber:
    """
    Whisper 语音转写器
    
    使用 faster-whisper 实现高效的本地语音转写
    """
    
    def __init__(
        self,
        model_size: str = None,
        language: str = None,
        device: str = "auto"
    ):
        """
        初始化转写器
        
        Args:
            model_size: 模型大小 (base/small/medium/large)
            language: 语言代码 (zh/en/auto)
            device: 设备 (cpu/cuda/auto)
        """
        config = get_config()
        self.model_size = model_size or config.WHISPER_MODEL
        self.language = language or config.WHISPER_LANGUAGE
        self.device = device
        
        self._model = None
        self._model_path = None
    
    def _load_model(self):
        """加载 Whisper 模型"""
        if self._model is not None:
            return
        
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "faster-whisper 未安装。请运行：\n"
                "  pip install faster-whisper\n\n"
                "或者使用 OpenAI Whisper API 模式"
            )
        
        print(f"[转写] 加载模型: {self.model_size} (语言: {self.language})...")
        
        # 确定设备
        if self.device == "auto":
            if os.getenv("CUDA_VISIBLE_DEVICES"):
                self.device = "cuda"
            else:
                self.device = "cpu"
        
        # 选择模型路径（如果本地有缓存）
        model_path = self._get_cached_model_path()
        
        if model_path and os.path.exists(model_path):
            print(f"[转写] 使用缓存模型: {model_path}")
            self._model = WhisperModel(
                model_path,
                device=self.device,
                compute_type="float16" if self.device == "cuda" else "int8"
            )
        else:
            # 下载模型
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="float16" if self.device == "cuda" else "int8"
            )
        
        print(f"[转写] 模型加载完成，设备: {self.device}")
    
    def _get_cached_model_path(self) -> Optional[str]:
        """获取缓存的模型路径"""
        # HuggingFace 缓存
        hf_home = os.getenv("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
        hub_path = os.path.join(hf_home, "hub")
        
        if os.path.exists(hub_path):
            # 查找 faster-whisper 模型
            for name in os.listdir(hub_path):
                if name.startswith("ffn_weights_"):
                    return os.path.join(hub_path, name)
        
        return None
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: str = None
    ) -> Dict[str, Any]:
        """
        转写音频为文字
        
        Args:
            audio: numpy 音频数组 (float32, 范围 -1.0 ~ 1.0)
            language: 语言代码，None 则使用初始化时的语言
        
        Returns:
            Dict包含:
                - text: 转写文字
                - language: 检测到的语言
                - segments: 分段信息
                - confidence: 置信度
        """
        self._load_model()
        
        language = language or self.language
        
        # 确保音频是 float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # 确保音频范围在 -1.0 ~ 1.0
        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = audio / max(abs(audio.max()), abs(audio.min()))
        
        print(f"[转写] 开始转写，音频长度: {len(audio)/16000:.1f}秒...")
        
        # 执行转写
        segments, info = self._model.transcribe(
            audio,
            language=language if language != "auto" else None,
            beam_size=5,
            vad_filter=True,  # 语音活动检测
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # 收集结果
        full_text = []
        segment_list = []
        
        for seg in segments:
            segment_list.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })
            full_text.append(seg.text.strip())
        
        result = {
            "text": " ".join(full_text),
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": segment_list,
            "duration": len(audio) / 16000
        }
        
        print(f"[转写] 转写完成: {result['text'][:50]}...")
        
        return result
    
    def transcribe_file(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        """
        转写音频文件
        
        Args:
            audio_path: 音频文件路径 (wav/mp3/mp4 等)
            language: 语言代码
        
        Returns:
            转写结果
        """
        # 加载音频
        import wave
        
        with wave.open(audio_path, 'rb') as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            
            # 读取帧
            frames = wf.readframes(n_frames)
            
            # 转换为 numpy 数组
            if sample_width == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 4:
                audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                audio = np.frombuffer(frames, dtype=np.float32)
            
            # 转换为单声道
            if channels > 1:
                audio = audio.reshape(-1, channels).mean(axis=1)
            
            # 重采样（如果需要）
            if sample_rate != 16000:
                import scipy.signal
                num_samples = int(len(audio) * 16000 / sample_rate)
                audio = scipy.signal.resample(audio, num_samples)
                sample_rate = 16000
        
        return self.transcribe(audio, language)
    
    @staticmethod
    def download_model(model_size: str, output_dir: str = None) -> str:
        """
        下载并缓存模型
        
        Args:
            model_size: 模型大小
            output_dir: 输出目录
        
        Returns:
            模型路径
        """
        from faster_whisper import WhisperModel
        
        output_dir = output_dir or os.path.expanduser("~/.cache/whisper")
        
        print(f"[转写] 下载模型 {model_size} 到 {output_dir}...")
        
        # faster-whisper 会自动下载
        model = WhisperModel(model_size)
        
        return output_dir


class OpenAIWhisperTranscriber:
    """
    OpenAI Whisper API 转写器（备用方案）
    
    当本地转写不可用时使用
    """
    
    def __init__(self, api_key: str = None, model: str = "whisper-1"):
        from openai import OpenAI
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("需要设置 OPENAI_API_KEY 环境变量")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def transcribe(self, audio_path: str, language: str = "zh") -> str:
        """
        使用 OpenAI Whisper API 转写
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
        
        Returns:
            转写文字
        """
        print(f"[转写] 使用 OpenAI Whisper API 转写: {audio_path}...")
        
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language if language != "auto" else None,
                response_format="text"
            )
        
        return response


def test_transcriber():
    """测试转写功能"""
    print("测试 Whisper 转写...")
    
    # 检查 faster-whisper 是否可用
    try:
        import faster_whisper
        print("faster-whisper 已安装")
    except ImportError:
        print("faster-whisper 未安装，尝试安装...")
        os.system("pip install faster-whisper")
    
    transcriber = WhisperTranscriber(model_size="base")
    
    # 检查是否有测试音频
    test_file = "test_recording.wav"
    if os.path.exists(test_file):
        result = transcriber.transcribe_file(test_file)
        print(f"转写结果: {result['text']}")
    else:
        print(f"测试文件不存在: {test_file}")


if __name__ == "__main__":
    test_transcriber()
