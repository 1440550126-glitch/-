"""语音对话：录音 → 转写 → Agent → TTS 朗读。能力探测，缺组件时优雅提示。

录音/识别/合成均依赖系统工具（arecord/sox/ffmpeg、whisper、say/espeak），
存在即用，不存在则清楚说明，不伪装能力。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile

_RECORDERS = [
    ("arecord", lambda f, s: ["arecord", "-q", "-d", str(s), "-f", "cd", f]),
    ("sox", lambda f, s: ["sox", "-d", f, "trim", "0", str(s)]),
    ("ffmpeg", lambda f, s: ["ffmpeg", "-y", "-f", "alsa", "-i", "default", "-t", str(s), f]),
]


def recorder() -> str | None:
    return next((c for c, _ in _RECORDERS if shutil.which(c)), None)


def record(seconds: int, out: str) -> str | None:
    for cmd, build in _RECORDERS:
        if shutil.which(cmd):
            try:
                subprocess.run(build(out, seconds), capture_output=True, timeout=seconds + 10)
                return cmd
            except Exception:  # noqa: BLE001
                return None
    return None


def transcribe(path: str) -> str | None:
    for cmd in ("whisper", "whisper-cli", "whisper-cpp"):
        if shutil.which(cmd):
            try:
                r = subprocess.run([cmd, path], capture_output=True, text=True, timeout=600)
                return (r.stdout or "").strip() or None
            except Exception:  # noqa: BLE001
                return None
    return None


def speak(text: str) -> bool:
    for cmd, build in (("say", lambda t: ["say", t]), ("spd-say", lambda t: ["spd-say", t]),
                       ("espeak-ng", lambda t: ["espeak-ng", t]), ("espeak", lambda t: ["espeak", t])):
        if shutil.which(cmd):
            try:
                subprocess.run(build(text), capture_output=True, timeout=60)
                return True
            except Exception:  # noqa: BLE001
                return False
    return False


def missing() -> list[str]:
    miss = []
    if not recorder():
        miss.append("录音(arecord/sox/ffmpeg)")
    if not any(shutil.which(c) for c in ("whisper", "whisper-cli", "whisper-cpp")):
        miss.append("识别(whisper)")
    if not any(shutil.which(c) for c in ("say", "spd-say", "espeak-ng", "espeak")):
        miss.append("合成(say/espeak)")
    return miss


def converse_once(app, seconds: int = 5) -> str:
    """录一句 → 转写 → 跑 Agent → 朗读。返回过程文本说明。"""
    miss = missing()
    if "录音(arecord/sox/ffmpeg)" in miss or "识别(whisper)" in miss:
        return "语音输入不可用，缺少：" + "、".join(miss) + "。可改用文本对话。"
    wav = tempfile.mktemp(suffix=".wav")
    if not record(seconds, wav):
        return "录音失败。"
    text = transcribe(wav)
    if not text:
        return "没听清（转写为空）。"
    reply = app.agent.run(text, session="voice")
    spoke = speak(reply)
    return f"你说：{text}\nMnemo：{reply}" + ("" if spoke else "\n（无 TTS，仅文字）")
