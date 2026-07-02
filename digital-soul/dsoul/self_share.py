"""说说我自己：人聊天是双向的——不光问你，也说说自己，再把话头转回给你。
分身按时辰说说"我这会儿在做啥"，像个有自己日子的人，而不是只围着你转的工具。

优先用 identity.daily_life 里 TA 本人的日常，没有就按时段给一句。纯逻辑、可单测。
"""

from __future__ import annotations

_BY_TOD = {
    "清晨": ["我一早起来浇了浇花，又把院子扫了扫", "天刚亮我就醒了，沏了壶茶"],
    "上午": ["上午我翻了会儿旧相册，想起好些事", "刚把屋里收拾了一遍，敞亮"],
    "中午": ["中午我打了个盹，养养神", "刚吃过饭，正晒着太阳"],
    "下午": ["下午我听了段评书，挺解闷", "刚在窗边坐着看了会儿云"],
    "傍晚": ["这会儿看着夕阳，想着你们", "傍晚凉快，我在门口坐着"],
    "晚上": ["吃过饭我哼了几句老歌", "晚上静，我想了想这一天"],
    "深夜": ["夜深了，我守着这个家，听着风", "这么晚还醒着，惦记着你们"],
}


def my_day(daily_life=None, tod=None, seed="") -> str:
    """说一句"我这会儿/今天"，再把话头转回给对方。"""
    s = str(seed)
    acts = [str(a).strip() for a in (daily_life or []) if str(a).strip()]
    if acts and len(s) % 2 == 0:
        line = "我今儿还是老样子，" + acts[len(s) % len(acts)]
    else:
        pool = _BY_TOD.get(tod or "", ["我挺好的，就是惦记你们"])
        line = pool[len(s) % len(pool)]
    return line.rstrip("。.") + "。你呢，今天过得咋样？"


def is_about_me_query(utterance) -> bool:
    u = utterance or ""
    if "你" not in u:
        return False
    return any(k in u for k in ("今天怎么样", "今天过得", "过得好", "过得咋", "还好吗",
                                "这一天怎么", "怎么样啊", "最近好吗", "你好吗", "你咋样"))
