#!/usr/bin/env python3
"""用"克隆的本人嗓音"念一句话——模型无关的薄包装（合成 → 播放，带兜底）。

把各家开源声音大模型（GPT-SoVITS / CosyVoice / Fish-Speech…）统一成一条命令：
输入文字 → 合成 wav → 播放。接到 `config/identity.yaml` 的 `voice.tts_cmd` 即可。

设计要点：
  · 纯逻辑可单测：命令拼装、播放器选择、兜底判断都是独立函数；
  · 绝不哑掉：引擎没接好 / 没装播放器，就回落到系统 say/espeak（dsoul.voice.Mouth）。

用法：
  python scripts/say_clone.py --engine gpt-sovits --ref voices/mom.wav "你回来啦"
  python scripts/say_clone.py --engine system "外面冷不冷"      # 直接走系统嗓音

接你自己的模型：改 build_synth_cmd() 里对应引擎那几行（标了 # TODO）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from urllib.parse import quote

DEFAULT_OUT = os.path.join(os.environ.get("TMPDIR", "/tmp"), "dsoul_say.wav")

# 常见命令行播放器，按优先级探测（Mac:afplay / Linux:aplay,paplay / 通用:ffplay）
_PLAYERS = ("afplay", "aplay", "paplay", "ffplay")


def gpt_sovits_url(text, host="127.0.0.1", port=9880, lang="zh") -> str:
    """GPT-SoVITS `api.py` 起服务后的合成 URL（文字已转义）。"""
    return f"http://{host}:{port}/?text={quote(str(text))}&text_language={lang}"


def build_synth_cmd(engine, text, ref=None, out=DEFAULT_OUT) -> list | None:
    """拼一条"把 text 合成到 out(wav)"的命令（list）。

    engine 为 system / 未知，返回 None —— 交给系统 TTS 兜底。
    各引擎这几行就是给你改的：换成你本地真实的调用方式（# TODO）。
    """
    e = (engine or "").strip().lower()
    if e in ("gpt-sovits", "gptsovits", "sovits"):
        # TODO 接你的 GPT-SoVITS：默认走它自带的 HTTP api.py
        return ["curl", "-s", gpt_sovits_url(text), "-o", out]
    if e in ("cosyvoice", "cosy", "cosyvoice2"):
        # TODO 接你的 CosyVoice：把 cosyvoice_cli 换成你的 CLI/脚本
        cmd = ["python", "-m", "cosyvoice_cli", "--text", str(text), "--out", out]
        if ref:
            cmd += ["--prompt", ref]
        return cmd
    if e in ("fish", "fish-speech", "openaudio"):
        # TODO 接你的 Fish-Speech / OpenAudio
        cmd = ["fish-speech", "--text", str(text), "--output", out]
        if ref:
            cmd += ["--reference", ref]
        return cmd
    return None


def play_cmd(path, which=shutil.which) -> list | None:
    """挑一个可用的命令行播放器来放 path；都没有则 None。"""
    for p in _PLAYERS:
        exe = which(p)
        if exe:
            if p == "ffplay":
                return [exe, "-nodisp", "-autoexit", "-loglevel", "quiet", path]
            return [exe, path]
    return None


def synthesize(engine, text, ref=None, out=DEFAULT_OUT,
               runner=subprocess.run, which=shutil.which, exists=os.path.exists) -> bool:
    """跑合成命令，成功产出音频返回 True；引擎没接 / 二进制缺失 / 出错都返回 False。"""
    cmd = build_synth_cmd(engine, text, ref, out)
    if not cmd or not which(cmd[0]):
        return False
    try:
        runner(cmd, check=False, timeout=120)
    except Exception:
        return False
    try:
        return bool(exists(out))
    except Exception:
        return False


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


def say(text, engine="system", ref=None, out=DEFAULT_OUT) -> str:
    """念一句：先用克隆嗓音（合成+播放），不成就回落系统嗓音。返回走的哪条路。"""
    if synthesize(engine, text, ref, out) and play(out):
        return "clone"
    # 兜底：绝不让分身突然哑掉
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dsoul.voice import Mouth
        Mouth().speak(str(text))
    except Exception:
        print(str(text))
    return "fallback"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="用克隆嗓音念一句话（带系统嗓音兜底）")
    ap.add_argument("--engine", default="system",
                    help="gpt-sovits / cosyvoice / fish / system")
    ap.add_argument("--ref", default=None, help="参考音频（克隆音色用的那段录音）")
    ap.add_argument("--out", default=DEFAULT_OUT, help="合成 wav 的落地路径")
    ap.add_argument("text", nargs="+", help="要念的话")
    return ap.parse_args(argv)


def main(argv=None) -> None:
    a = parse_args(argv)
    route = say(" ".join(a.text), engine=a.engine, ref=a.ref, out=a.out)
    if route == "fallback" and a.engine not in ("system", ""):
        print(f"（提示：引擎 {a.engine} 没就绪，已用系统嗓音兜底——见 docs/voice_clone.md）")


if __name__ == "__main__":
    main()
