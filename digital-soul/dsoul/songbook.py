"""歌本：有了嗓音，分身就该会唱两句——不只哼个调，还能唱出词、教你唱、跟你接龙对唱。
给屋里添点活气，也给那些"小时候妈总哼这个"的念想，一个能接上的下一句。

只收**传唱已久、广为流传的传统/民歌/童谣**的几句词（《茉莉花》《送别》《东方红》…），
现代版权歌只哼调子、不录整词。纯逻辑、可单测。配在 config/music.yaml 的 lyrics。
"""

from __future__ import annotations

# 传统/公有领域老调的几句词（按传唱顺序）。键是带书名号的歌名。
_LYRICS = {
    "《茉莉花》": ["好一朵美丽的茉莉花", "好一朵美丽的茉莉花",
                  "芬芳美丽满枝桠", "又香又白人人夸"],
    "《送别》": ["长亭外，古道边", "芳草碧连天",
                "晚风拂柳笛声残", "夕阳山外山"],
    "《东方红》": ["东方红，太阳升", "中国出了个毛泽东",
                  "他为人民谋幸福", "他是人民大救星"],
    "《康定情歌》": ["跑马溜溜的山上", "一朵溜溜的云哟",
                    "端端溜溜的照在", "康定溜溜的城哟"],
    "《沂蒙山小调》": ["人人那个都说哎", "沂蒙山好",
                      "沂蒙那个山上哎", "好风光"],
    "《小白船》": ["蓝蓝的天空银河里", "有只小白船",
                  "船上有棵桂花树", "白兔在游玩"],
    "《友谊地久天长》": ["怎能忘记旧日朋友", "心中能不怀想",
                        "旧日朋友岂能相忘", "友谊地久天长"],
    "《二月里来》": ["二月里来好春光", "家家户户种田忙",
                    "指望着今年的收成好", "多捐些五谷充军粮"],
}


def known_songs() -> list:
    """歌本里有词、能唱出来的歌。"""
    return list(_LYRICS.keys())


def _merge(config) -> dict:
    """配置里的 lyrics 合并进默认歌本（配置优先、可加新歌）。"""
    db = dict(_LYRICS)
    if isinstance(config, dict) and isinstance(config.get("lyrics"), dict):
        for k, v in config["lyrics"].items():
            lines = [str(x).strip() for x in (v or []) if str(x).strip()]
            if lines:
                key = k if str(k).startswith("《") else f"《{k}》"
                db[key] = lines
    return db


_PUNC = "，,。.！!？?、；;：:\"“”‘’… 　\n\t《》「」"


def _bare(s) -> str:
    """剥掉标点和空白，只留字，便于"东方红，太阳升"≈"东方红太阳升"地比对。"""
    return "".join(ch for ch in str(s or "") if ch not in _PUNC)


def _norm_title(song) -> str:
    s = str(song or "").strip()
    if s and not s.startswith("《"):
        s = f"《{s}》"
    return s


def lyric_lines(song, config=None) -> list:
    """某首歌的几句词；歌本里没有就空。"""
    return list(_merge(config).get(_norm_title(song), []))


def sing(song=None, config=None, mood=None, seed="") -> str:
    """唱一首：有词就唱出头两句、招呼你和一句；没词就哼个调子。"""
    db = _merge(config)
    title = _norm_title(song)
    if title:                                      # 指定了歌：有词就唱，没词就哼这首
        if title not in db:
            from .music import hum
            return hum(config, seed=song)
    else:                                          # 没指定：从爱唱的、且有词的里挑一首
        from .music import favorites
        favs = [s for s in favorites(config) if s in db] or list(db.keys())
        title = favs[len(str(seed)) % len(favs)] if favs else ""
    lines = db.get(title, [])
    if not lines:
        from .music import hum
        return hum(config, seed=seed)
    head = "，".join(lines[:2]).rstrip("，")
    return f"（唱起{title}）“{head}……” 你跟我和一句呗？"


def next_lyric(song, line, config=None) -> str:
    """对唱接龙：给一句词，返回这首歌的下一句；到尾了或对不上返回空。"""
    lines = lyric_lines(song, config)
    cur = _bare(line)
    for i, ln in enumerate(lines[:-1]):
        a = _bare(ln)
        if a and (a in cur or cur in a):
            return lines[i + 1]
    return ""


def recognize(fragment, config=None) -> str:
    """听句词猜歌名（"这是哪首歌"）。对不上返回空。"""
    frag = _bare(fragment)
    if not frag:
        return ""
    for title, lines in _merge(config).items():
        for ln in lines:
            a = _bare(ln)
            if a and (a in frag or frag in a):
                return title
    return ""


def lead_singalong(song=None, config=None, seed="") -> str:
    """起个头领唱，请你接下一句。"""
    db = _merge(config)
    title = _norm_title(song)
    if not (title and title in db):
        keys = list(db.keys())
        title = keys[len(str(seed)) % len(keys)] if keys else ""
    lines = db.get(title, [])
    if not lines:
        return "想唱哪首？你起个头，我跟你和。"
    return f"来，我起个头，你接下一句啊——{title}：“{lines[0]}……”"


def is_sing_request(utterance) -> bool:
    u = utterance or ""
    if any(k in u for k in ("一起唱", "合唱", "对唱", "我们唱", "咱俩唱", "接龙唱")):
        return False                       # 这些归"合唱/接龙"，不在这判
    return any(k in u for k in ("唱给我听", "给我唱", "唱一句", "唱两句", "唱出来",
                                "唱完整", "唱整首", "唱词", "你唱"))


def is_singalong(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("一起唱", "合唱", "对唱", "我们唱", "咱俩唱", "接龙唱",
                                "陪我唱", "和我唱"))


def wants_lyrics(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("歌词", "词是啥", "词是什么", "怎么唱", "下一句",
                                "后面怎么唱", "接下一句"))


def is_recognize_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("这是什么歌", "这是哪首歌", "什么歌来着", "哪首歌",
                                "这歌叫啥", "什么歌唱的", "刚才那首"))
