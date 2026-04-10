# -*- coding: utf-8 -*-
"""
Voice Agent - 配置管理
"""

import os
from typing import Optional


class Config:
    """语音代理配置"""
    
    # 音频配置
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 1024
    
    # Whisper 配置
    WHISPER_MODEL = "medium"  # base / small / medium / large
    WHISPER_LANGUAGE = "zh"
    
    # 录音配置
    RECORD_TIMEOUT = 30.0  # 最大录音时长（秒）
    SILENCE_THRESHOLD = 0.01  # 静音阈值
    SILENCE_DURATION = 2.0  # 静音持续多少秒后停止
    
    # LLM 校正配置
    LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "MiniMax-Text-01")
    
    # 快捷键
    PUSH_TO_TALK_KEY = "space"  # 空格键
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        config = cls()
        
        if os.getenv("WHISPER_MODEL"):
            config.WHISPER_MODEL = os.getenv("WHISPER_MODEL")
        
        if os.getenv("WHISPER_LANGUAGE"):
            config.WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE")
        
        return config


def get_config() -> Config:
    """获取配置实例"""
    return Config.from_env()
