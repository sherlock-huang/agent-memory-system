# -*- coding: utf-8 -*-
"""
Voice Agent - 音频录制模块
支持多种录音后端：sounddevice / pyaudio / speech_recognition
"""

import io
import time
import wave
import numpy as np
from typing import Optional, Tuple

from .config import get_config


class AudioRecorder:
    """
    音频录制器
    
    支持多种后端，按优先级尝试：
    1. sounddevice (推荐，跨平台)
    2. pyaudio
    3. speech_recognition (仅作为备用)
    """
    
    def __init__(
        self,
        sample_rate: int = None,
        channels: int = None,
        chunk_size: int = None
    ):
        config = get_config()
        self.sample_rate = sample_rate or config.SAMPLE_RATE
        self.channels = channels or config.CHANNELS
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        
        self._stream = None
        self._backend = None
        self._sd = None
        self._pa = None
    
    def _try_import_sounddevice(self):
        """尝试导入 sounddevice"""
        try:
            import sounddevice as sd
            self._sd = sd
            self._backend = "sounddevice"
            return True
        except ImportError:
            return False
    
    def _try_import_pyaudio(self):
        """尝试导入 pyaudio"""
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self._backend = "pyaudio"
            return True
        except ImportError:
            return False
    
    def _init_backend(self):
        """初始化音频后端"""
        if self._backend:
            return
        
        if self._try_import_sounddevice():
            return
        
        if self._try_import_pyaudio():
            return
        
        raise RuntimeError(
            "无法找到音频录制库。请安装以下任一库：\n"
            "  pip install sounddevice  # 推荐\n"
            "  pip install pyaudio"
        )
    
    def record(self, duration: Optional[float] = None) -> Tuple[np.ndarray, int]:
        """
        录制音频
        
        Args:
            duration: 录音时长（秒），None 表示手动停止
        
        Returns:
            Tuple[音频数据, 采样率]
        """
        self._init_backend()
        
        if self._backend == "sounddevice":
            return self._record_sounddevice(duration)
        elif self._backend == "pyaudio":
            return self._record_pyaudio(duration)
    
    def _record_sounddevice(self, duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """使用 sounddevice 录制"""
        print(f"[录音] 开始录音（最常 {duration or '手动停止'}秒）...")
        
        audio_data = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"[警告] {status}")
            audio_data.append(indata.copy())
        
        try:
            with self._sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=callback
            ):
                if duration:
                    time.sleep(duration)
                else:
                    # 等待手动停止
                    input("按 Enter 停止录音...\n")
        except KeyboardInterrupt:
            pass
        
        if not audio_data:
            return np.array([], dtype=np.float32), self.sample_rate
        
        # 合并所有音频块
        audio = np.concatenate(audio_data, axis=0)
        
        # 转换为单声道
        if self.channels > 1:
            audio = audio.mean(axis=1)
        
        print(f"[录音] 录音完成，时长: {len(audio) / self.sample_rate:.1f}秒")
        
        return audio, self.sample_rate
    
    def _record_pyaudio(self, duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """使用 pyaudio 录制"""
        print(f"[录音] 开始录音（最常 {duration or '手动停止'}秒）...")
        
        audio_data = []
        
        def callback(in_data, frame_count, time_info, status):
            audio_data.append(np.frombuffer(in_data, dtype=np.float32))
            return None, pyaudio.paContinue
        
        stream = self._pa.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=callback
        )
        
        stream.start_stream()
        
        try:
            if duration:
                time.sleep(duration)
            else:
                input("按 Enter 停止录音...\n")
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
        
        if not audio_data:
            return np.array([], dtype=np.float32), self.sample_rate
        
        audio = np.concatenate(audio_data)
        
        print(f"[录音] 录音完成，时长: {len(audio) / self.sample_rate:.1f}秒")
        
        return audio, self.sample_rate
    
    def record_to_wav(self, output_path: str, duration: Optional[float] = None) -> bool:
        """
        录制音频并保存为 WAV 文件
        
        Args:
            output_path: 输出文件路径
            duration: 录音时长
        
        Returns:
            是否成功
        """
        audio, sr = self.record(duration)
        
        if len(audio) == 0:
            return False
        
        # 转换为 int16
        audio_int16 = (audio * 32767).astype(np.int16)
        
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())
        
        print(f"[录音] 已保存到: {output_path}")
        return True
    
    def close(self):
        """关闭音频后端"""
        if self._pa:
            self._pa.terminate()
            self._pa = None


def test_recorder():
    """测试录音功能"""
    print("测试音频录制...")
    
    recorder = AudioRecorder()
    
    try:
        audio, sr = recorder.record(duration=3)
        print(f"录制成功！采样率: {sr}Hz, 时长: {len(audio)/sr:.1f}秒")
        
        # 保存测试文件
        test_file = "test_recording.wav"
        import wave
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(recorder.channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        print(f"测试音频已保存: {test_file}")
        
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    test_recorder()
