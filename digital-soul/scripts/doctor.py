#!/usr/bin/env python3
"""开机自检：一次性检查 大模型 / 记忆 / 语音 / 摄像头 / 人脸 / 界面 是否就绪。

用法：python scripts/doctor.py
⚠️ 的项目都是可选能力，不装也能跑（自动降级）；❌ 才是必须修。
"""

import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

OK, WARN, BAD = "✅", "⚠️", "❌"


def line(status: str, name: str, detail: str = "", hint: str = "") -> None:
    print(f"{status} {name}" + (f" — {detail}" if detail else ""))
    if status != OK and hint:
        print(f"     ↳ {hint}")


def _imp(name: str):
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def main() -> None:
    print("🩺 数字分身自检")
    print("=" * 52)

    v = sys.version_info
    line(OK if v >= (3, 9) else WARN, "Python", f"{v.major}.{v.minor}.{v.micro}", "建议 3.9+")

    if _imp("yaml"):
        line(OK, "PyYAML", "已安装")
    else:
        line(BAD, "PyYAML", "缺失（必需）", "pip install pyyaml")

    agent = None
    try:
        from dsoul.loader import build_agent

        agent = build_agent()
        line(OK, "身份/关系配置", f"{len(agent.authority.people)} 个人物")
        line(OK, "记忆库", f"{len(agent.memory.items)} 条 · 检索={agent.memory.embedder.mode}")
    except Exception as e:
        line(BAD, "框架装配", str(e)[:50], "检查 config/identity.yaml、relationships.yaml")

    try:
        from dsoul.llm import LLM

        m = LLM()
        line(
            OK if m.available else WARN,
            "本地大模型(Ollama)",
            f"{m.host} · {m.model} · {'连通' if m.available else '未连通'}",
            "装 Ollama 或设 DSOUL_LLM_HOST 指向局域网；不接也能降级运行",
        )
    except Exception as e:
        line(WARN, "本地大模型", str(e)[:40])

    stt = "faster-whisper" if _imp("faster_whisper") else ("openai-whisper" if _imp("whisper") else "")
    line(OK if stt else WARN, "语音转文字", stt or "未安装", "pip install faster-whisper")

    line(OK if _imp("pyttsx3") else WARN, "文字转语音", "pyttsx3" if _imp("pyttsx3") else "未安装",
         "pip install pyttsx3（Linux 还需 espeak-ng）")

    line(OK if _imp("sounddevice") else WARN, "麦克风(sounddevice)",
         "可用" if _imp("sounddevice") else "未安装",
         "pip install sounddevice + apt install portaudio19-dev")

    if not _imp("cv2"):
        line(WARN, "摄像头(opencv)", "未安装", "pip install opencv-python")
    else:
        import cv2

        cap = cv2.VideoCapture(0)
        opened = cap.isOpened()
        cap.release()
        line(OK if opened else WARN, "摄像头", "已打开" if opened else "未检测到设备")

    nfaces = len(getattr(agent.perception, "known", {})) if agent is not None else 0
    if not _imp("face_recognition"):
        line(WARN, "人脸识别", "未安装", "pip install face_recognition")
    else:
        line(OK if nfaces else WARN, "人脸识别", f"{nfaces} 张已登记人脸",
             "用 scripts/ingest.py face <id> <图片> 登记")

    line(OK if _imp("tkinter") else WARN, "桌面界面(tkinter)",
         "可用" if _imp("tkinter") else "未安装", "sudo apt install python3-tk")

    print("=" * 52)
    print("说明：⚠️ 的是可选能力，不装也能跑（自动降级）；❌ 才需修复。")


if __name__ == "__main__":
    main()
