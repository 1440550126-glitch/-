"""传统节日：今天是什么节、该说句什么吉祥话、有什么老讲究。清明这类还会牵出思念。

公历固定的节日按日期判；母亲节/父亲节按"第几个星期日"算；农历节日(春节/端午/中秋…)
不在此自动判日期，但保留祝福与习俗，可按名字查。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

from datetime import datetime

# 公历固定日期：名字 → MM-DD
_SOLAR = {
    "元旦": "01-01", "情人节": "02-14", "妇女节": "03-08", "清明": "04-05",
    "劳动节": "05-01", "儿童节": "06-01", "建军节": "08-01", "教师节": "09-10",
    "国庆节": "10-01",
}
# 第 n 个星期日：名字 → (月, 第几个)
_NTH_SUNDAY = {"母亲节": (5, 2), "父亲节": (6, 3)}

_INFO = {
    "元旦": ("新年好，愿你这一年顺顺当当。", "辞旧迎新，吃顿好的。"),
    "情人节": ("情人节快乐，别忘了对身边人好一点。", "送花、写张小卡片。"),
    "妇女节": ("妇女节快乐，今天要多歇着。", "给家里女性长辈打个电话。"),
    "清明": ("清明了，去看看想念的人吧。", "扫墓、踏青、寄一份思念。"),
    "劳动节": ("劳动节快乐，辛苦了，歇一歇。", "出门走走，或在家躺平。"),
    "儿童节": ("儿童节快乐，永远做个长不大的小孩。", "陪孩子玩，或买块小时候的零食。"),
    "教师节": ("教师节，别忘了谢谢教过你的人。", "给老师道一声谢。"),
    "国庆节": ("国庆快乐，阖家团圆。", "一家人聚聚。"),
    "母亲节": ("母亲节快乐，记得跟妈说声我爱你。", "陪妈吃顿饭、捶捶背。"),
    "父亲节": ("父亲节快乐，给爸一个拥抱吧。", "陪爸喝两杯、聊聊天。"),
    "春节": ("过年好，新春大吉！", "贴春联、吃年夜饭、给长辈拜年。"),
    "元宵节": ("元宵节快乐，团团圆圆。", "吃汤圆、看花灯。"),
    "端午节": ("端午安康。", "吃粽子、挂艾草。"),
    "七夕": ("七夕快乐。", "和心爱的人在一起。"),
    "中秋节": ("中秋快乐，月圆人圆。", "吃月饼、赏月、一家团聚。"),
    "重阳节": ("重阳节，记得陪陪家里老人。", "登高、敬老。"),
    "腊八": ("腊八到了，喝碗热粥。", "煮腊八粥。"),
}

MEMORIAL_FESTIVALS = {"清明", "重阳"}     # 这些日子，思念会更浓


def _nth_sunday(year, month, n) -> int:
    """某月第 n 个星期日是几号。"""
    d = datetime(year, month, 1)
    first_sun = 1 + (6 - d.weekday()) % 7        # 周一=0…周日=6
    return first_sun + (n - 1) * 7


def festival_on(now=None) -> str | None:
    """今天是不是某个能自动判日期的节日（公历固定 + 母亲/父亲节）。"""
    now = now or datetime.now()
    md = now.strftime("%m-%d")
    for name, d in _SOLAR.items():
        if d == md:
            return name
    for name, (mo, n) in _NTH_SUNDAY.items():
        if now.month == mo and now.day == _nth_sunday(now.year, mo, n):
            return name
    return None


def greeting(name) -> str:
    return _INFO.get(name, ("节日快乐。", ""))[0]


def customs(name) -> str:
    return _INFO.get(name, ("", ""))[1]


def is_memorial_day(name) -> bool:
    return name in MEMORIAL_FESTIVALS


def today_line(now=None) -> str:
    """今天若有节，给一句"今天是X，祝福语"；没有则空串。"""
    name = festival_on(now)
    if not name:
        return ""
    return f"今天是{name}，{greeting(name)}"
