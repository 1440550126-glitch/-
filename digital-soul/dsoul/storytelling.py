"""讲古 / 家庭故事会：分身爱给后辈讲故事——想当年的家史、怎么熬过苦日子、
和老伴怎么认识的……也能给小孩讲个睡前故事。挑一个，带着开场白娓娓道来，轮着讲不重样。

故事来自 config/stories.yaml，或记忆库里 source 标了 story 的条目。纯逻辑、可单测。
"""

from __future__ import annotations

_OPEN = ["我跟你讲个事啊", "想当年呐", "说起这个，我想起一桩", "来，听我讲段古"]
_CLOSE = ["——这事我记一辈子。", "——日子啊，就是这么过来的。", "——你也记着点。"]
_BED = ["乖，闭上眼睛，给你讲个故事。", "躺好咯，听我慢慢讲。"]


def collect_stories(config=None, memory_items=None) -> list:
    """汇总故事：[{title, story, tags, kind}, ...]，按正文去重保序。"""
    out, seen = [], set()

    def _add(title, story, tags=None, kind="家史"):
        story = str(story or "").strip()
        if not story or story in seen:
            return
        seen.add(story)
        out.append({"title": str(title or "").strip(), "story": story,
                    "tags": [str(t).strip() for t in (tags or [])], "kind": kind})

    for s in ((config or {}).get("stories") or []) if isinstance(config, dict) else []:
        if isinstance(s, dict):
            _add(s.get("title"), s.get("story") or s.get("text"),
                 s.get("tags"), s.get("kind", "家史"))
        elif isinstance(s, str):
            _add("", s)
    for it in (memory_items or []):
        if isinstance(it, dict) and "story" in str(it.get("source", "")):
            _add("", it.get("text"))
    return out


def pick_story(stories, topic=None, exclude=None):
    """挑一个故事：尽量避开 exclude（已讲过的正文）；有 topic 就挑最沾边的。"""
    exclude = set(exclude or [])
    pool = [s for s in stories if s["story"] not in exclude] or list(stories or [])
    if not pool:
        return None
    if topic:
        chars = set(str(topic))
        best, score = None, 0
        for s in pool:
            hay = s["title"] + " " + " ".join(s["tags"]) + " " + s["story"]
            c = sum(1 for ch in chars if ch in hay)
            if c > score:
                best, score = s, c
        if best is not None:
            return best
    return pool[0]


def tell(story, bedtime=False) -> str:
    """娓娓道来：开场白 + 正文 + 收尾（按正文长度选措辞，可单测）。"""
    if not story:
        return ""
    n = len(story["story"])
    opener = (_BED[n % len(_BED)] if bedtime else _OPEN[n % len(_OPEN)])
    close = "" if bedtime else _CLOSE[n % len(_CLOSE)]
    body = story["story"].rstrip("。.")
    return f"{opener}——{body}。{close}" if not bedtime else f"{opener}——{body}。"


def titles(stories) -> list:
    """报一报肚子里都有哪些故事。"""
    return [(s["title"] or (s["story"][:12] + "…")) for s in (stories or [])]
