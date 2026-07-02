"""稳住心神：心慌、喘不匀、静不下来、坐立不安时，带你做个简单的呼吸/着地练习，
把人从慌乱里慢慢拉回来。不是看病，是当下能用的小法子。present-tense、可单测。

（胸口疼/喘不上气这类是身体急症，归 emergency 处理，本模块只管"心里的慌"。）
"""

from __future__ import annotations

_ANX = ("心慌", "慌得", "慌神", "静不下", "静不下来", "坐立不安", "心里发慌", "心神不宁",
        "紧张得", "喘不匀", "心跳得厉害", "六神无主", "慌乱", "稳不住")

_BREATH = ("来，跟我做个深呼吸——鼻子慢慢吸气，数四下：1、2、3、4。 "
           "屏住，数七下。 再用嘴缓缓吐出来，数八下。 咱再来一轮，慢慢的，不急。")

_GROUND = ("别慌，跟我把心收回来——先说出你眼前看得到的五样东西。 "
           "再摸摸身边四样东西，感觉它们是凉是暖。 听听三种声音。 闻闻两种味道。 "
           "最后，深吸一口气——你是安全的，我就在这儿。")


def senses_anxiety(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _ANX)


def breathing() -> str:
    return _BREATH


def grounding() -> str:
    return _GROUND


def calm(utterance="", name="", seed="") -> str:
    """把人稳住：先一句安抚，再按情况带个呼吸或着地练习。"""
    who = (str(name) + "，") if name else ""
    head = f"{who}我在，别怕，咱一起把心慢慢稳下来。"
    body = _GROUND if (len(str(seed or utterance)) % 2 == 0) else _BREATH
    return f"{head} {body}"
