#!/usr/bin/env python3
"""生成喵语通语音包 voicepack.bin（烧到 voices 分区）。

两种素材来源：
  1) TTS 批量合成（默认）：  python make_voice_pack.py --phrases phrases.json --out voicepack.bin
     依赖: pip install edge-tts；系统需有 ffmpeg
  2) 自己录的音频：          python make_voice_pack.py --wav-dir ./my_wavs --out voicepack.bin
     文件命名: class0_xxx.wav / class1_xxx.wav / class2_xxx.wav（class 后数字=类别 ID）

二进制格式（小端，与 firmware/main/voice.c 严格对应）：
  header: magic "MVPK" | u16 version=1 | u16 count
  entry × count: u8 class_id | u8 flags | u16 pad | u32 offset | u32 length
  data: 各条 16kHz/16bit/mono 原始 PCM，4 字节对齐
"""
import argparse
import asyncio
import json
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

SAMPLE_RATE = 16000
MAGIC = b"MVPK"
VERSION = 1


def wav_to_pcm(path: Path) -> bytes:
    """任意 wav → 16k/16bit/mono 原始 PCM（经 ffmpeg 重采样）"""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "-"],
        capture_output=True, check=True)
    return out.stdout


async def tts_phrases(phrases_file: Path, tmp: Path) -> list[tuple[int, Path]]:
    import edge_tts
    spec = json.loads(phrases_file.read_text(encoding="utf-8"))
    voice = spec.get("tts_voice", "zh-CN-XiaoyiNeural")
    items = []
    for cls in spec["classes"]:
        for i, text in enumerate(cls["phrases"]):
            mp3 = tmp / f"class{cls['id']}_{i}.mp3"
            print(f"  TTS [{cls['name']}] {text}")
            await edge_tts.Communicate(text, voice).save(str(mp3))
            items.append((cls["id"], mp3))
    return items


def collect_wav_dir(wav_dir: Path) -> list[tuple[int, Path]]:
    items = []
    for p in sorted(wav_dir.glob("class*_*.wav")):
        cls = int(p.stem.split("_")[0].removeprefix("class"))
        items.append((cls, p))
    if not items:
        sys.exit(f"{wav_dir} 下没有 classN_*.wav 文件")
    return items


def pack(items: list[tuple[int, bytes]], out: Path) -> None:
    header_size = 8 + len(items) * 12
    data_start = (header_size + 3) & ~3          # 数据区 4 字节对齐
    entries, blobs = [], []
    offset = data_start
    for cls, pcm in items:
        entries.append(struct.pack("<BBHII", cls, 0, 0, offset, len(pcm)))
        padded = pcm + b"\x00" * (-len(pcm) % 4)  # 每条对齐到 4 字节
        blobs.append(padded)
        offset += len(padded)
    data = struct.pack("<4sHH", MAGIC, VERSION, len(items))
    data += b"".join(entries)
    data += b"\x00" * (data_start - header_size)
    data += b"".join(blobs)
    out.write_bytes(data)
    dur = sum(len(p) for _, p in items) / 2 / SAMPLE_RATE
    print(f"✅ {out}: {len(items)} 条语音, 共 {dur:.1f}s, {len(data)/1024:.0f} KB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrases", type=Path, help="phrases.json（TTS 模式）")
    ap.add_argument("--wav-dir", type=Path, help="自录音频目录（classN_*.wav）")
    ap.add_argument("--out", type=Path, default=Path("voicepack.bin"))
    args = ap.parse_args()
    if not args.phrases and not args.wav_dir:
        ap.error("--phrases 或 --wav-dir 至少给一个")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if args.wav_dir:
            raw = collect_wav_dir(args.wav_dir)
        else:
            raw = asyncio.run(tts_phrases(args.phrases, tmp))
        items = [(cls, wav_to_pcm(p)) for cls, p in raw]
    pack(items, args.out)
    print("烧录: parttool.py --port <PORT> write_partition "
          f"--partition-name voices --input {args.out}")


if __name__ == "__main__":
    main()
