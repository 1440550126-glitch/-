#!/usr/bin/env python3
"""语音体检：在你的机器上一条条查清楚——能不能听、能不能说、克隆嗓音接没接通，
没装的告诉你怎么补。最后还会用你配置的嗓音真的念一句，听个响。

用法：
  python scripts/voice_doctor.py            # 体检 + 试说一句
  python scripts/voice_doctor.py --no-say   # 只体检，不出声
  python scripts/voice_doctor.py --text "外面冷不冷"   # 自己指定试说的话
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.voice import diagnose, format_diagnostics  # noqa: E402


def _load_profile():
    """从 config/identity.yaml 读 voice 档案（含 tts_cmd）；读不到就空。"""
    try:
        import yaml
        p = pathlib.Path(__file__).resolve().parent.parent / "config" / "identity.yaml"
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data.get("voice") or {}
    except Exception:
        return {}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="数字分身·语音链路体检")
    ap.add_argument("--no-say", action="store_true", help="只体检，不试说")
    ap.add_argument("--text", default="你好，我在这儿陪着你。", help="试说的话")
    args = ap.parse_args(argv)

    profile = _load_profile()
    checks = diagnose(profile=profile)
    print(format_diagnostics(checks))

    can_speak = any(n == "说·合成嗓音" and ok for n, ok, *_ in checks)
    if args.no_say or not can_speak:
        if not can_speak:
            print("\n（没有可用的合成引擎，跳过试说。把上面 ❌ 的「说」补上再来。）")
        return

    print(f"\n🔊 试说一句（用你配置的嗓音）：「{args.text}」")
    try:
        from dsoul.voice import Mouth
        Mouth().speak(args.text, profile=profile)
        print("   如果刚才出声了，说明链路通了。要换成本人声线，配上 voice.tts_cmd（见 docs/voice_clone.md）。")
    except Exception as e:
        print(f"   试说出错：{e}")


if __name__ == "__main__":
    main()
