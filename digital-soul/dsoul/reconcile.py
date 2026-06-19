"""放下：心里搁着跟谁的旧怨、没说出口的对不起、当年的悔——分身轻轻劝你放下、
趁还来得及去说、去和好。不催不逼，是陪你把那口气松开。present-tense、可单测。
"""

from __future__ import annotations

# (类别, 触发词, 宽慰话)
_KINDS = [
    ("愧疚", ("对不起他", "对不起她", "对不起你们", "愧疚", "亏欠", "过意不去", "没脸见"),
     "心里过意不去，正说明你重情重义。趁还来得及，去说一声、去补一句——开口了，心就松了。"),
    ("记恨", ("没原谅", "不原谅", "记恨", "怨他", "怨她", "咽不下这口气", "过不去那道坎"),
     "记恨这事，最熬的其实是自己。退一步，把那口气慢慢松开，你会轻快好多——不是为了谁，是为了你自己。"),
    ("后悔", ("后悔", "当年要是", "早知道", "悔不当初", "要是当初"),
     "后悔的事，谁这辈子没几桩。可日子是往前过的——能补的去补，补不了的，就放过自己，别再拿它磨心。"),
    ("心结", ("心结", "解不开", "想不通", "一直放不下", "搁在心里"),
     "这心结搁久了，沉。慢慢来，先跟我念叨念叨，说出来就轻一半，咱一点点把它解开。"),
]


def senses_regret(utterance) -> bool:
    u = utterance or ""
    return any(any(k in u for k in kws) for _c, kws, _r in _KINDS)


def soothe_regret(utterance, name="") -> str:
    """认同那份重，再轻轻劝放下/去和好。"""
    u = utterance or ""
    who = (str(name) + "，") if name else ""
    for _c, kws, resp in _KINDS:
        if any(k in u for k in kws):
            return who + resp
    return ""
