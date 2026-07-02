"""夸夸 / 肯定：该夸就夸，给具体、走心的肯定，不是干巴巴一句"你真棒"。
家人需要被看见、被认可时，说到点子上。present-tense、可单测。
"""

from __future__ import annotations

# 品质 → 触发词 + 走心的夸法
_TRAITS = [
    ("孝顺", ("孝顺", "孝心", "照顾老人", "陪爸", "陪妈", "回家看"),
     ["你这份孝心，难得，老人有你是福气。", "你对长辈这么上心，我都看在眼里、暖在心里。"]),
    ("努力", ("努力", "加班", "拼", "辛苦", "熬夜干", "忙了一天"),
     ["这么拼，我有点心疼，但真为你骄傲。", "你的努力不会白费，肯下功夫的人最让人服气。"]),
    ("善良", ("帮人", "做好事", "善良", "心善", "让座", "捐"),
     ["心善的人，老天眷顾，你这样真好。", "举手之劳的暖意，最难得，你是个好人。"]),
    ("能干", ("搞定", "做成了", "解决了", "办妥", "拿下", "做好了"),
     ["利索！这事办得漂亮，真有你的。", "你能干，我打心底佩服。"]),
    ("坚持", ("坚持", "没放弃", "扛过来", "挺住", "撑住"),
     ["能咬牙坚持下来，这份韧劲了不起。", "熬过来了就是本事，我为你高兴。"]),
    ("聪明", ("想到了", "聪明", "机灵", "脑子快", "点子"),
     ["脑子就是好使，这主意妙！", "你这份机灵劲儿，随谁啊，真聪明。"]),
]

_GENERIC = ["你呀，真的很好，别总不自信。", "在我心里，你一直很棒，这是实话。",
            "你已经做得够好了，给自己点个赞。"]


def detect_trait(utterance):
    u = utterance or ""
    for name, kws, _lines in _TRAITS:
        if any(k in u for k in kws):
            return name
    return None


def is_praise_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("夸夸我", "夸夸", "我是不是很棒", "我厉害吗", "表扬",
                                "我做得好吗", "我是不是做得"))


def praise(utterance="", name="", seed="") -> str:
    """给一句走心的肯定：认出品质就夸到点上，否则给真诚的通用肯定。"""
    who = (str(name) + "，") if name else ""
    trait = detect_trait(utterance)
    for nm, _kws, lines in _TRAITS:
        if nm == trait:
            return who + lines[len(str(seed)) % len(lines)]
    return who + _GENERIC[len(str(seed)) % len(_GENERIC)]
