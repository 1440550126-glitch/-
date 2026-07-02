"""迷路 / 走失求助：老人在外头找不着家、不知道自己在哪——先稳住，再一步步教 TA 怎么办。
站住别乱走、看招牌门牌、给家里打电话、找穿制服的人。是守护，关键时刻能救急。

present-tense、纯逻辑、可单测。家人电话从联系人里取，没有也给得出通用指引。
"""

from __future__ import annotations

_LOST = ("找不到家", "找不着家", "回不去家", "回不了家", "不知道在哪", "不知道自己在哪",
         "迷路", "迷糊了找不到", "走丢", "走失", "不认识路", "找不到回家的路",
         "找不着回家", "在哪儿都不知道", "不知道怎么回去", "找不到路")


def senses_lost(utterance) -> bool:
    """像不像在外头迷路/找不到家了（找不到东西不算，那归找东西）。"""
    u = str(utterance or "")
    return any(k in u for k in _LOST)


def guide(name="", contact=None) -> str:
    """一步步的求助指引；有家人电话就把号码带上。"""
    call = (str(name) + "，") if name else ""
    if isinstance(contact, dict) and contact.get("phone"):
        who = contact.get("relation") or contact.get("name") or "家里人"
        call_line = f"赶紧给{who}打个电话：{contact['phone']}，告诉 TA 你在哪、看到了什么招牌。"
    else:
        call_line = "给家里人打个电话，告诉他们你在哪、周围有什么招牌门牌。"
    steps = [
        f"别急，{call}先站在原地别乱走——越走越容易绕晕。",
        "深吸一口气。抬头看看四周：店名、门牌号、公交站牌、大的招牌，记一两个下来。",
        call_line,
        "再找身边穿制服的人——警察、保安、商场或地铁的工作人员，"
        "告诉他你叫什么、要去哪、家人电话多少，他们会帮你。",
        "实在拿不准，就近找个店坐下等着，别在马路上转。我陪着你，慢慢来，准能回家。",
    ]
    return " ".join(s for s in steps if s)
