#!/usr/bin/env python3
"""用 MiniMax 云端嗓音念一句话——合成 → 落地 → 播放（出错就非零退出，好让上层回落）。

接到 config/identity.yaml 的 voice.tts_cmd：
  tts_cmd: "python scripts/minimax_say.py {text}"

密钥只从环境变量读：
  export MINIMAX_API_KEY=sk-...        # 必填（别写进代码/配置/仓库）
  export MINIMAX_VOICE_ID=...          # 选填：你的克隆音色 id（不填用内置温暖女声）
  export MINIMAX_GROUP_ID=...          # 选填：部分账号需要

设计要点（和 say_clone.py 一致）：
  · 合成失败 / 没密钥 / 没播放器 → 退出码非零，voice.Mouth 会自动回落系统嗓音，绝不哑掉；
  · 纯逻辑（拼请求/解音频）在 dsoul.minimax_tts 里，可离线单测。

单独验证：
  python scripts/minimax_say.py "你回来啦，外面冷不冷？"
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.minimax_tts import synth  # noqa: E402

# 命令行播放器，按优先级探测（Mac:afplay / Linux:aplay,paplay / 通用:ffplay）
_PLAYERS = ("afplay", "aplay", "paplay", "ffplay")


def play_cmd(path, which=shutil.which) -> list | None:
    """挑一个可用的播放器放 path；都没有则 None。"""
    for p in _PLAYERS:
        exe = which(p)
        if exe:
            if p == "ffplay":
                return [exe, "-nodisp", "-autoexit", "-loglevel", "quiet", path]
            return [exe, path]
    return None


def play(path, runner=subprocess.run, which=shutil.which) -> bool:
    """播放 path；没有播放器或出错返回 False。"""
    cmd = play_cmd(path, which)
    if not cmd:
        return False
    try:
        runner(cmd, check=False, timeout=120)
        return True
    except Exception:
        return False


def say(text, fmt="mp3", out=None) -> str:
    """合成 + 播放一句。返回走的哪条路：ok / no-key / synth-fail / no-player。"""
    if not os.environ.get("MINIMAX_API_KEY"):
        return "no-key"
    out = out or os.path.join(os.environ.get("TMPDIR", "/tmp"), f"dsoul_minimax.{fmt}")
    try:
        audio = synth(text, fmt=fmt)
    except Exception as e:                       # 网络/密钥/余额/权限……都回落
        print(f"（MiniMax 合成失败：{e}）", file=sys.stderr)
        return "synth-fail"
    try:
        pathlib.Path(out).write_bytes(audio)
    except Exception as e:
        print(f"（写音频失败：{e}）", file=sys.stderr)
        return "synth-fail"
    return "ok" if play(out) else "no-player"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="用 MiniMax 云端嗓音念一句话")
    ap.add_argument("--format", default="mp3", help="音频格式 mp3/wav/pcm（默认 mp3）")
    ap.add_argument("--out", default=None, help="音频落地路径（默认临时目录）")
    ap.add_argument("text", nargs="+", help="要念的话")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    route = say(" ".join(a.text), fmt=a.format, out=a.out)
    if route == "ok":
        return 0
    hint = {
        "no-key": "没设 MINIMAX_API_KEY（export 进环境变量）",
        "synth-fail": "MiniMax 合成失败（见上面的报错；检查密钥/余额/网络）",
        "no-player": "合成好了但没找到播放器（Mac 自带 afplay；Linux 装 alsa-utils）",
    }.get(route, route)
    print(f"（MiniMax 没念成：{hint}——已交回上层用系统嗓音兜底）", file=sys.stderr)
    return 1                                      # 非零 → voice.Mouth 自动回落


if __name__ == "__main__":
    raise SystemExit(main())
