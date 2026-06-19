"""认民族乐器：二胡、古筝、琵琶、笛子……各是什么音色、有什么名曲。
听到一段曲子、看到一件乐器，能说出个门道，挺雅。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 乐器 → (类别/演奏方式, 音色, 名曲)
_INSTR = {
    "二胡": ("拉弦乐器，两根弦", "如泣如诉、婉转动人", "《二泉映月》《赛马》"),
    "古筝": ("弹拨乐器，二十一弦", "清亮悠扬、行云流水", "《渔舟唱晚》《高山流水》"),
    "古琴": ("弹拨乐器，七弦，文人雅器", "古朴深远、清微淡远", "《高山流水》《广陵散》"),
    "笛子": ("吹管乐器，竹制横吹", "清脆嘹亮、明快", "《姑苏行》《牧民新歌》"),
    "箫": ("吹管乐器，竖吹", "幽静低沉、含蓄", "《平湖秋月》《妆台秋思》"),
    "琵琶": ("弹拨乐器，四弦怀抱弹", "刚柔并济、珠落玉盘", "《十面埋伏》《阳春白雪》"),
    "唢呐": ("吹管乐器，喇叭口", "高亢嘹亮、穿透力强，红白喜事都用", "《百鸟朝凤》"),
    "笙": ("吹管乐器，一束竹管带簧", "和声丰富、清越", "《凤凰展翅》"),
    "扬琴": ("击弦乐器，竹键敲", "清脆明亮，民乐队里的‘钢琴’", "《将军令》"),
    "阮": ("弹拨乐器，圆音箱", "圆润浑厚", "《云南回忆》"),
    "锣鼓": ("打击乐器", "喜庆热闹、震天响，逢年过节舞龙舞狮少不了", "《老虎磨牙》"),
    "编钟": ("青铜打击乐器，一套大小钟", "庄严浑厚，几千年前的‘交响乐’", "曾侯乙编钟出土最有名"),
}

_ALIAS = {"胡琴": "二胡", "筝": "古筝", "横笛": "笛子", "竹笛": "笛子", "洞箫": "箫",
          "喇叭": "唢呐", "锣": "锣鼓", "鼓": "锣鼓"}


def _table(config) -> dict:
    db = dict(_INSTR)
    if isinstance(config, dict) and isinstance(config.get("instruments"), dict):
        for k, v in config["instruments"].items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                db[str(k)] = (str(v[0]), str(v[1]), str(v[2]))
    return db


def instruments(config=None) -> list:
    return list(_table(config))


def find_instrument(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_instrument(query, config)
    row = db.get(name)
    if not row:
        return ""
    kind, tone, songs = row
    return f"{name}：{kind}，音色{tone}。名曲有{songs}。"


def is_instrument_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("民族乐器", "传统乐器", "国乐")):
        return True
    if find_instrument(u, config) and any(k in u for k in ("是什么", "啥乐器", "什么乐器",
                                                           "音色", "名曲", "介绍", "怎么样",
                                                           "讲讲", "什么声", "好听")):
        return True
    return False
