"""声音相册：把本人留下的真实语音片段收着——那句口头禅、那声叮嘱、那阵笑。
在合适的时候放出来，让你**真的听见 TA**，而不只是合成的声儿。这是赛博永生最戳心的一块。

片段配在 config（voicebank: 一组 {file, text, occasions, mood, tags}）。
选片是纯逻辑、可单测；放音是尽力而为（有播放器就放，没有就把那句话端出来）。
"""

from __future__ import annotations

import os
import shutil
import subprocess

_PLAYERS = ("afplay", "aplay", "paplay", "ffplay")


def normalize_clip(raw) -> dict:
    """把一条配置规整成统一结构。"""
    if isinstance(raw, str):
        return {"file": "", "text": raw.strip(), "occasions": [], "mood": "", "tags": []}
    if not isinstance(raw, dict):
        return {}
    occ = raw.get("occasions") or raw.get("occasion") or []
    if isinstance(occ, str):
        occ = [occ]
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return {
        "file": str(raw.get("file", "")).strip(),
        "text": str(raw.get("text", "")).strip(),
        "occasions": [str(x).strip() for x in occ if str(x).strip()],
        "mood": str(raw.get("mood", "")).strip(),
        "tags": [str(x).strip() for x in tags if str(x).strip()],
    }


class VoiceBank:
    """本人真实语音片段的小册子：按场景/心情/关键词挑一段。"""

    def __init__(self, clips=None) -> None:
        self.clips = [c for c in (normalize_clip(x) for x in (clips or [])) if c.get("text") or c.get("file")]

    @classmethod
    def from_config(cls, config) -> "VoiceBank":
        raw = None
        if isinstance(config, dict):
            raw = config.get("voicebank") or config.get("voice_clips")
        return cls(raw if isinstance(raw, list) else None)

    def __len__(self) -> int:
        return len(self.clips)

    def all(self) -> list:
        return list(self.clips)

    def _score(self, clip, occasion, mood, keyword) -> int:
        s = 0
        if occasion and occasion in clip["occasions"]:
            s += 3
        if mood and mood == clip["mood"]:
            s += 2
        if keyword:
            if keyword in clip["text"]:
                s += 2
            if any(keyword in t for t in clip["tags"]):
                s += 1
        return s

    def pick(self, occasion=None, mood=None, keyword=None, seed="") -> dict | None:
        """挑最应景的一段；都不挑明就随手来一段。没有片段返回 None。"""
        if not self.clips:
            return None
        if not (occasion or mood or keyword):
            return self.clips[len(str(seed)) % len(self.clips)]
        best, best_s = None, 0
        for c in self.clips:
            s = self._score(c, occasion, mood, keyword)
            if s > best_s:
                best, best_s = c, s
        if best is None:                       # 有要求但都没匹配上 → 随手一段兜底
            return self.clips[len(str(seed)) % len(self.clips)]
        return best

    def for_occasion(self, occasion) -> list:
        return [c for c in self.clips if occasion in c["occasions"]]

    def search(self, keyword) -> list:
        k = str(keyword or "")
        if not k:
            return []
        return [c for c in self.clips if k in c["text"] or any(k in t for t in c["tags"])]


def describe(clip) -> str:
    """把要放的这段，端成一句话（放不出声时也让你看见那句话）。"""
    if not clip:
        return ""
    text = clip.get("text", "")
    return f"（放一段 TA 亲口说的）“{text}”" if text else "（放一段 TA 留下的声音）"


def _player(which=shutil.which):
    for p in _PLAYERS:
        exe = which(p)
        if exe:
            return p, exe
    return None, None


def play_clip(clip, runner=subprocess.run, which=shutil.which, exists=os.path.exists) -> bool:
    """尽力放出这段录音：有文件、有播放器才放。放成返回 True。"""
    if not clip:
        return False
    f = clip.get("file", "")
    if not f or not exists(f):
        return False
    name, exe = _player(which)
    if not exe:
        return False
    cmd = [exe, "-nodisp", "-autoexit", "-loglevel", "quiet", f] if name == "ffplay" else [exe, f]
    try:
        runner(cmd, check=False, timeout=120)
        return True
    except Exception:
        return False


def is_voicebank_request(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("放段录音", "放段你说", "放段他说", "放段她说", "听听你的声音",
                                "想听你的声音", "听听他说", "听听她说", "你录的话",
                                "你留的声音", "放你说的", "听你说话", "你的录音"))
