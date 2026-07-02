"""像人一样思考：收到一句话，先在心里转几个弯——这话什么意思、是不是话里有话、
我想起什么、心里怎么看、该怎么接。不是条件反射，是有思量的。

- read_subtext：听话听音，读出表面话底下的真意（"我没事"多半不是真没事）；
- ponder：把这思量过程拉成一串内心活动，让分身的脑子"转得见"；
- respond_to_subtext：照着读出的真意，给一句更懂人的话。

纯逻辑、可单测。有大模型时，这些判断会作为提示喂给它，让它回得更通人情。
"""

from __future__ import annotations

# 言外之意：类别 → (触发词, 心里的判断, 照着真意该怎么接)
_SUBTEXT = [
    ("强忍", ("我没事", "没事儿", "我挺好", "我能行", "不用管我", "别管我", "我没什么"),
     "嘴上说没事，多半是心里有事、不想让人担心。",
     "{who}嘴上说没事，可我瞧着你不太对劲。别自己扛着，跟我念叨念叨。"),
    ("嘴硬", ("我不饿", "我不累", "我不冷", "不用麻烦", "不碍事", "我扛得住"),
     "TA 嘴硬，其实是怕给人添麻烦。",
     "{who}别逞强，该吃吃、该歇歇，照顾好自己我才安心。"),
    ("憋气", ("怎么还没", "老是这样", "总是这样", "烦死了", "又来了", "够了啊"),
     "话里带着气，与其跟TA讲理，不如先把情绪接住。",
     "{who}听你这话是憋着火呢，先消消气，有啥不痛快慢慢跟我说。"),
    ("欲言又止", ("算了", "没什么好说", "不说了", "当我没说", "说了你也不懂"),
     "TA 有话没说出口，别追问，给个台阶等TA愿意讲。",
     "{who}有话就慢慢说，不急；说不出口也没关系，我都在。"),
    ("自责", ("都怪我", "我没用", "我真没用", "是我不好", "拖累你们", "拖累家里", "我对不起"),
     "TA 在自责，这会儿最需要被肯定、被宽慰，不是被分析。",
     "{who}别老怪自己，你已经做得够好了，这事真不怨你。"),
]


def read_subtext(utterance):
    """读出言外之意，返回 (类别, 心里的判断)；读不出返回 (None, "")。"""
    u = utterance or ""
    for cat, kws, insight, _resp in _SUBTEXT:
        if any(k in u for k in kws):
            return cat, insight
    return None, ""


def respond_to_subtext(utterance, who="") -> str:
    """照着读出的真意，给一句更懂人的话。"""
    u = utterance or ""
    for _cat, kws, _insight, resp in _SUBTEXT:
        if any(k in u for k in kws):
            return resp.format(who=(str(who) + "，") if who else "")
    return ""


def ponder(utterance, speaker=None, memories=None, mood=None, knows=None) -> list:
    """像人一样在心里转几个弯，返回一串思量（可作内心活动展示）。"""
    steps = []
    rel = (speaker or {}).get("relation") if isinstance(speaker, dict) else None
    if rel:
        steps.append(f"是{rel}在跟我说话，得用心听。")
    if knows:                                    # 用上我对TA一直以来的了解
        steps.append(f"我了解你——{knows}，顺着这点想。")
    _cat, insight = read_subtext(utterance)
    if insight:
        steps.append(insight)
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if mems:
        steps.append(f"这让我想起：{mems[0].rstrip('。.')}。")
    if mood and mood not in ("平静", None):
        steps.append(f"我这会儿心里有点{mood}，可别带到话里。")
    steps.append("我想想，怎么接才妥帖——")
    return steps


def thinking_hint(utterance) -> str:
    """把读出的真意写成一句给大模型的提示（让它回得更通人情）。"""
    _cat, insight = read_subtext(utterance)
    return (f"（弦外之音：{insight} 回应时把这层意思照顾到，别只接字面。）") if insight else ""
