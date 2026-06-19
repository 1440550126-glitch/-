#!/usr/bin/env python3
"""语音对话：说话 → 语音转文字 → 数字分身回应 → 语音播报。

可选依赖：faster-whisper（听）、pyttsx3（说）、sounddevice+numpy（麦克风录音）。
缺哪个就自动退化为键盘输入 / 打印输出，闭环仍然能体验。

用法：python scripts/voice_chat.py
"""

import pathlib
import sys
import tempfile
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402
from dsoul.voice import Ears, Mouth  # noqa: E402


def record(seconds: int = 5, samplerate: int = 16000) -> str | None:
    """录一段麦克风音频存成 wav，返回路径。没有 sounddevice 则返回 None。"""
    try:
        import numpy as np  # noqa: F401
        import sounddevice as sd
    except Exception:
        return None
    print(f"🎙️  录音 {seconds}s（请说话）...")
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    path = tempfile.mktemp(suffix=".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(samplerate)
        w.writeframes(audio.tobytes())
    return path


def _owner(agent) -> str:
    for p in agent.authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return "我"


def main() -> None:
    agent = build_agent()
    ears, mouth = Ears(), Mouth()
    name = agent.identity.get("name", "我")
    speaker = _owner(agent)
    profile = agent.identity.get("voice")        # 本人嗓音档案（语速/音量/系统嗓音/克隆命令）
    print(f"🎧 语音对话 | 听:{ears.backend or '无→键盘'} | 说:{mouth.backend or '无→打印'}")
    if mouth.backend in ("say", "espeak-ng", "espeak"):
        print(f"   ✅ 用系统自带语音「{mouth.backend}」出声，零安装。"
              + ("（Mac 想换中文女声：config/identity.yaml 里 voice.voice 填 Tingting）"
                 if mouth.backend == "say" else ""))
    elif mouth.backend is None:
        print("   ⚠️ 没找到语音引擎。Mac 自带 say 通常就有；Linux 可 `apt install espeak-ng`；"
              "或 `pip install pyttsx3`。")
    print("（说/输入 退出 结束）")

    while True:
        text = None
        if ears.available:
            wav = record()
            text = ears.transcribe(wav) if wav else None
            if text:
                print(f"你说: {text}")
        if not text:
            try:
                text = input(f"{speaker} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
        if not text:
            continue
        if text in ("退出", "quit", "/quit", "exit"):
            break
        res = agent.handle(speaker, text)
        print(f"{name}: {res['reply']}")
        mood = None
        if getattr(agent, "emotions", None) is not None:
            try:
                mood = agent.emotions.mood()[0]
            except Exception:
                mood = None
        mouth.speak(res["reply"], mood=mood, profile=profile)   # 带情绪 + 本人嗓音说出来


if __name__ == "__main__":
    main()
