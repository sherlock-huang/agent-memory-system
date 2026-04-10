#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voice Agent CLI - 命令行入口
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.recorder import AudioRecorder
from scripts.transcriber import WhisperTranscriber
from scripts.corrector import TranscriptCorrector, SimpleCorrector


def voice_to_text(duration: float = None, use_llm: bool = True):
    """
    语音输入 → 转写 → 校正 → 输出文字
    
    Args:
        duration: 录音时长（秒）
        use_llm: 是否使用 LLM 校正
    """
    print("=" * 50)
    print("Voice Agent - 语音输入模式")
    print("=" * 50)
    
    # 1. 录音
    print("\n[1/3] 准备录音...")
    recorder = AudioRecorder()
    
    try:
        audio, sr = recorder.record(duration=duration)
    except Exception as e:
        print(f"录音失败: {e}")
        return None
    finally:
        recorder.close()
    
    if len(audio) == 0:
        print("没有录到音频")
        return None
    
    # 保存临时文件
    import wave
    import tempfile
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav.close()
    
    with wave.open(temp_wav.name, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((audio * 32767).astype('<h2').tobytes())
    
    # 2. 转写
    print("\n[2/3] 转写中...")
    transcriber = WhisperTranscriber(model_size="base")
    
    try:
        result = transcriber.transcribe_file(temp_wav.name)
        original_text = result["text"]
    except Exception as e:
        print(f"转写失败: {e}")
        os.unlink(temp_wav.name)
        return None
    
    # 3. 校正
    print("\n[3/3] 校正中...")
    
    if use_llm:
        try:
            corrector = TranscriptCorrector()
            corrected_text = corrector.correct(original_text)
        except Exception as e:
            print(f"LLM 校正失败，使用简单校正: {e}")
            corrected_text = SimpleCorrector.correct(original_text)
    else:
        corrected_text = SimpleCorrector.correct(original_text)
    
    # 清理
    os.unlink(temp_wav.name)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("转写结果:")
    print("=" * 50)
    print(f"原始: {original_text}")
    print(f"校正: {corrected_text}")
    print("=" * 50)
    
    return corrected_text


def correct_text(text: str, use_llm: bool = True):
    """
    直接校正文字
    
    Args:
        text: 输入文字
        use_llm: 是否使用 LLM
    """
    print(f"输入: {text}")
    
    if use_llm:
        try:
            corrector = TranscriptCorrector()
            result = corrector.correct(text)
        except Exception as e:
            print(f"LLM 校正失败: {e}")
            result = SimpleCorrector.correct(text)
    else:
        result = SimpleCorrector.correct(text)
    
    print(f"校正: {result}")
    return result


def test_all():
    """测试所有模块"""
    print("=" * 50)
    print("Voice Agent - 模块测试")
    print("=" * 50)
    
    # 测试录音
    print("\n[测试] 录音模块...")
    try:
        recorder = AudioRecorder()
        print(f"  录音器初始化成功，后端: {recorder._backend}")
        recorder.close()
        print("  ✓ 录音模块正常")
    except Exception as e:
        print(f"  ✗ 录音模块失败: {e}")
    
    # 测试转写
    print("\n[测试] 转写模块...")
    try:
        transcriber = WhisperTranscriber(model_size="base")
        print(f"  转写器初始化成功，模型: {transcriber.model_size}")
        print("  ✓ 转写模块正常")
    except Exception as e:
        print(f"  ✗ 转写模块失败: {e}")
    
    # 测试校正
    print("\n[测试] 简单校正模块...")
    test_cases = [
        "把昆仑的生日存到记忆",
        "python怎么定义函数",
        "open claw今天天气",
    ]
    for text in test_cases:
        result = SimpleCorrector.correct(text)
        print(f"  '{text}' → '{result}'")
    print("  ✓ 简单校正模块正常")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Agent - 语音交互工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # listen 子命令
    listen_parser = subparsers.add_parser("listen", help="语音输入模式")
    listen_parser.add_argument(
        "--duration", "-d",
        type=float,
        default=None,
        help="录音时长（秒）"
    )
    listen_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用 LLM 校正"
    )
    
    # correct 子命令
    correct_parser = subparsers.add_parser("correct", help="校正文字")
    correct_parser.add_argument("text", help="要校正的文字")
    correct_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用 LLM 校正"
    )
    
    # test 子命令
    subparsers.add_parser("test", help="测试所有模块")
    
    args = parser.parse_args()
    
    if args.command == "listen":
        voice_to_text(duration=args.duration, use_llm=not args.no_llm)
    elif args.command == "correct":
        correct_text(args.text, use_llm=not args.no_llm)
    elif args.command == "test":
        test_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
