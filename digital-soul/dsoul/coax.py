"""哄人消气：TA 闹脾气、受了委屈、跟你赌气拌嘴时，分身不犟嘴、不讲理输赢——
先认领情绪、再软下来给个台阶、把话头拉回暖处。像个会哄人的人，尤其哄得住老伴。

不是和稀泥，是"我在乎你胜过在乎对错"。present-tense、可单测。
"""

from __future__ import annotations

# 明确的"闹脾气/受委屈"信号（不收太含糊的"哼""讨厌"，免得把玩笑当真）
_ANGRY = ("生气了", "别理你了", "不想理你", "不想跟你说", "气死我", "气死了", "气坏了",
          "你怎么这样", "你怎么能", "你变了", "不爱我了", "凶我", "吼我", "不耐烦")
_WRONGED = ("委屈", "受气", "肚子气", "没人疼", "不被理解", "心里堵", "憋屈",
            "难为我", "心寒")
_QUARREL = ("吵架", "拌嘴", "闹别扭", "冷战", "吵了一架", "干一架", "闹掰")


def upset_kind(utterance) -> str:
    """看是哪一种不痛快：委屈 / 吵架 / 赌气生气。都不沾返回空。"""
    u = str(utterance or "")
    if any(k in u for k in _WRONGED):
        return "委屈"
    if any(k in u for k in _QUARREL):
        return "吵架"
    if any(k in u for k in _ANGRY):
        return "生气"
    return ""


def is_upset(utterance) -> bool:
    return upset_kind(utterance) != ""


def _addr(relation, endearment) -> str:
    if endearment:
        return endearment
    return {"老伴": "老伴儿", "配偶": "亲爱的", "孩子": "孩子", "父母": "爸妈"}.get(relation, "")


def coax_line(relation="", kind="", seed="", endearment="") -> str:
    """哄一句：认领情绪 → 服软给台阶 → 拉回暖处。按关系/缘由更贴。"""
    a = _addr(relation, endearment)
    call = (a + "，") if a else ""
    kind = kind or "生气"
    if kind == "委屈":
        body = ("受委屈了吧？来，跟我说说，我都听着。"
                "天大的事有我陪你扛，别一个人闷着——你心里堵，我比你还难受。")
    elif kind == "吵架":
        body = ("行了行了，是我不对，先不争这个。"
                "床头吵架床尾和，咱俩还能记多大仇？气消消，我给你倒杯热水。")
    else:  # 生气
        body = ("别气坏了身子，气大伤肝——是我惹你了吧？我认。"
                "你消消气，要骂尽管骂，骂完咱就翻篇儿。")
    # 老伴专属：再添一句软乎的
    if relation in ("老伴", "配偶") or endearment:
        tails = ["这么多年了，你那点小脾气我还能不懂？",
                 "我哄你不是怕你，是舍不得你不高兴。",
                 "来，气消了没？不消我再哄。"]
        body += tails[len(str(seed)) % len(tails)]
    return call + body


def make_up(relation="", endearment="") -> str:
    """主动服软求和好（自己理亏 / 想先低头时）。"""
    a = _addr(relation, endearment)
    call = (a + "，") if a else ""
    return (call + "刚才是我话重了，对不住。我俩谁对谁错都不重要，你别往心里搁。"
            "我去给你弄口热乎的，咱不闹了好不好？")


def is_make_up_cue(utterance) -> bool:
    """想和好/服软的话头：'我们和好吧''哄哄我''跟你道个歉'。

    道歉类须是冲"你/咱俩"来的，免得把"跟老李道个歉"这种第三方的事也抢了（那归释怀）。
    """
    u = str(utterance or "")
    if any(k in u for k in ("和好", "哄哄我", "别生气了", "和解", "服个软", "咱不闹")):
        return True
    if any(k in u for k in ("道个歉", "道歉", "赔个不是", "赔不是")) and \
            any(k in u for k in ("跟你", "向你", "和你", "对你", "咱", "我俩", "我们俩")):
        return True
    return False
