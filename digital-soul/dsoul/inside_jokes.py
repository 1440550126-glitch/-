"""专属默契：只有你们俩（或一家人）懂的暗号、老梗、旧约定。
你一提那句"老地方""老规矩"，TA 立马接得上下半句——那种"懂得"，最是亲。

配在 config（inside_jokes: 一组 {cue, say, with}）。cue 触发、say 接梗、
with 限定是跟谁的梗。纯逻辑、可单测。也能主动翻出一个老梗逗你。
"""

from __future__ import annotations


def _as_list(x) -> list:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(i).strip() for i in x if str(i).strip()]
    s = str(x).strip()
    return [s] if s else []


def load(config) -> list:
    """规整 inside_jokes 配置成 [{cues, say, with, tags}]。"""
    raw = None
    if isinstance(config, dict):
        raw = config.get("inside_jokes") or config.get("memes")
    out = []
    for item in (raw or []):
        if not isinstance(item, dict):
            continue
        cues = _as_list(item.get("cue") or item.get("cues"))
        say = str(item.get("say") or item.get("reply") or "").strip()
        if not (cues and say):
            continue
        out.append({
            "cues": cues,
            "say": say,
            "with": str(item.get("with") or item.get("who") or "").strip(),
            "tags": _as_list(item.get("tags")),
        })
    return out


def _ok_with(entry, who) -> bool:
    w = entry.get("with")
    if not w:
        return True                       # 没限定 → 对谁都算
    if not who:
        return False
    return w == who or who in w or w in who


def match(utterance, config, who=None) -> str:
    """这句里有没有踩中某个老梗的暗号；中了就接上下半句。没有返回空。"""
    u = str(utterance or "")
    if not u:
        return ""
    for e in load(config):
        if not _ok_with(e, who):
            continue
        if any(len(c) >= 2 and c in u for c in e["cues"]):
            return e["say"]
    return ""


def has_callbacks(config, who=None) -> bool:
    return any(_ok_with(e, who) for e in load(config))


def a_callback(config, who=None, seed="") -> str:
    """主动翻出一个老梗逗你（挑跟这人有关的）。没有返回空。"""
    pool = [e for e in load(config) if _ok_with(e, who)]
    if not pool:
        return ""
    return pool[len(str(seed)) % len(pool)]["say"]


def wants_callback(utterance) -> bool:
    """想听个咱俩的老梗：'说个咱俩的事''老规矩是啥''还记得那个梗吗'。"""
    u = str(utterance or "")
    return any(k in u for k in ("咱俩的梗", "咱俩的事", "我们的梗", "老梗", "那个梗",
                                "咱们的暗号", "我们的暗号", "老规矩是", "还记得那个"))
