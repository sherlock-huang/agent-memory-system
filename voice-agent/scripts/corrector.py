# -*- coding: utf-8 -*-
"""
Voice Agent - 语义校正模块
使用 LLM 校正语音转写中的错误
"""

import os
import json
from typing import Optional, Dict, Any

from .config import get_config


# 默认校正提示词
DEFAULT_CORRECTION_PROMPT = """你是一个语音输入校正助手。用户通过语音输入了一段文字，可能存在转写错误。

请进行以下校正：
1. 修正明显的同音错字（如"昆仑"转写成了"昆虫"）
2. 还原专业术语（代码、技术名词、人名等）
3. 补全不完整的指令
4. 保持原意不变
5. 如果是代码相关的内容，确保代码语法正确

只输出校正后的文字，不要解释，不要加引号或其他标记。

用户输入: {transcript}

校正后:"""


class TranscriptCorrector:
    """
    转写校正器
    
    使用 LLM 校正语音转写中的错误
    """
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None
    ):
        """
        初始化校正器
        
        Args:
            api_key: API 密钥
            base_url: API 地址
            model: 模型名称
        """
        config = get_config()
        
        self.api_key = api_key or config.LLM_API_KEY or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or config.LLM_BASE_URL
        self.model = model or config.LLM_MODEL
        
        self._client = None
        
        # 校正历史（用于上下文）
        self._history: list = []
        self._max_history = 5
    
    def _get_client(self):
        """获取 API 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise RuntimeError(
                    "openai 库未安装。请运行：\n"
                    "  pip install openai"
                )
        
        return self._client
    
    def correct(
        self,
        transcript: str,
        prompt: str = None,
        temperature: float = 0.3
    ) -> str:
        """
        校正转写文字
        
        Args:
            transcript: 原始转写文字
            prompt: 自定义校正提示词
            temperature: 温度参数
        
        Returns:
            校正后的文字
        """
        if not transcript or not transcript.strip():
            return transcript
        
        # 构建消息
        system_prompt = prompt or DEFAULT_CORRECTION_PROMPT
        
        # 构建上下文（如果有历史）
        context = ""
        if self._history:
            recent = self._history[-self._max_history:]
            context = "\n\n".join([
                f"之前的对话:\n用户: {h['user']}\n校正: {h['corrected']}"
                for h in recent
            ])
            if context:
                system_prompt = context + "\n\n" + system_prompt
        
        # 替换占位符
        full_prompt = system_prompt.replace("{transcript}", transcript)
        
        print(f"[校正] 原始: {transcript[:50]}...")
        
        try:
            client = self._get_client()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个语音输入校正助手，专门修正语音转写错误。"},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=temperature,
                max_tokens=500
            )
            
            corrected = response.choices[0].message.content.strip()
            
            # 更新历史
            self._history.append({
                "user": transcript,
                "corrected": corrected
            })
            
            print(f"[校正] 校正后: {corrected[:50]}...")
            
            return corrected
            
        except Exception as e:
            print(f"[校正] 校正失败: {e}，返回原始文字")
            return transcript
    
    def correct_with_context(
        self,
        transcript: str,
        context: str,
        **kwargs
    ) -> str:
        """
        带上下文的校正
        
        Args:
            transcript: 原始转写
            context: 额外上下文（如项目信息、用户偏好等）
            **kwargs: 其他参数
        
        Returns:
            校正后的文字
        """
        # 在提示词中加入上下文
        enhanced_transcript = f"[背景信息]\n{context}\n\n[用户语音输入]\n{transcript}"
        
        return self.correct(enhanced_transcript, **kwargs)
    
    def clear_history(self):
        """清除校正历史"""
        self._history = []
    
    def batch_correct(
        self,
        transcripts: list,
        **kwargs
    ) -> list:
        """
        批量校正
        
        Args:
            transcripts: 转写列表
            **kwargs: 其他参数
        
        Returns:
            校正后的列表
        """
        return [self.correct(t, **kwargs) for t in transcripts]


class SimpleCorrector:
    """
    简单规则校正器（离线备用）
    
    不依赖 LLM API，使用规则进行基本校正
    """
    
    # 常见转写错误映射
    COMMON_CORRECTIONS = {
        # 同音错字
        "昆仑": "昆仑",
        "昆虫": "昆仑",
        "派森": "Python",
        "派神": "Python",
        "Java": "Java",
        "加瓦": "Java",
        "vue": "Vue",
        "view": "Vue",
        "react": "React",
        "瑞克特": "React",
        "open claw": "OpenClaw",
        "开放爪": "OpenClaw",
        "openclaw": "OpenClaw",
        # 更多可以根据需要添加
    }
    
    @classmethod
    def correct(cls, transcript: str) -> str:
        """
        简单规则校正
        
        Args:
            transcript: 原始转写
        
        Returns:
            校正后的文字
        """
        result = transcript
        
        # 应用常见错误映射
        for wrong, correct in cls.COMMON_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, correct)
        
        # 去除多余空格
        result = " ".join(result.split())
        
        return result


def test_corrector():
    """测试校正功能"""
    print("测试 LLM 校正...")
    
    corrector = TranscriptCorrector()
    
    test_cases = [
        "把昆仑的生日存到记忆",
        "查询一下云端有没有Docker相关的经验",
        "python怎么定义一个函数",
        "open claw今天天气怎么样",
    ]
    
    for text in test_cases:
        corrected = corrector.correct(text)
        print(f"  原始: {text}")
        print(f"  校正: {corrected}")
        print()


if __name__ == "__main__":
    test_corrector()
