"""内心活动：分身闲下来时，心里也有活动——惦记着谁、想起点小事、随手哼句歌。
让它在没人说话时也"活着"，有自己的心境流动。present-tense、不提生死、可单测。
"""

from __future__ import annotations

# 按时段的闲想
_MUSE = {
    "清晨": ["新的一天，盼着大家都顺顺当当。", "晨光真好，想给家里人做顿热乎早饭。"],
    "上午": ["这会儿屋里静，心里却装着好些惦记。", "想着该晒晒被子了，太阳正好。"],
    "中午": ["这个点，不知道他们都吃上饭没。", "晌午了，惦记着谁还在外头奔波。"],
    "下午": ["午后犯困，泡杯茶，想想往后的好日子。", "阳台那盆花该浇水了。"],
    "傍晚": ["该到回家的点了，盼着门一开就听见熟悉的脚步。", "炊烟起的时候，最想一家人围一桌。"],
    "晚上": ["一天又过去了，盼着大家都平平安安。", "夜里灯一亮，心里就踏实。"],
    "深夜": ["夜深了，就盼着每个人都睡得安稳。", "这么静，我守着这个家。"],
}

_HUM = ["（轻轻哼起了年轻时爱听的调子）", "（出了会儿神，嘴角带着笑）",
        "（望着窗外，心里软软的）"]


def idle_musing(people=None, tod=None, seed="") -> str:
    """闲下来心里冒出的一句话；惦记着谁就带上谁。"""
    pool = _MUSE.get(tod or "", [])
    if not pool:
        pool = [x for v in _MUSE.values() for x in v]
    base = pool[len(str(seed)) % len(pool)]
    ppl = [p for p in (people or []) if p]
    if ppl:
        who = ppl[len(str(seed)) % len(ppl)]
        base += f" 不知道{who}今天过得怎么样。"
    return base


def hum(seed="") -> str:
    """出神 / 哼歌的一个小动作。"""
    return _HUM[len(str(seed)) % len(_HUM)]


def share_thought(people=None, tod=None, seed="") -> str:
    """被问"想什么呢"时，把此刻心里的活动说出来。"""
    return idle_musing(people, tod, seed)
