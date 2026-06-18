"""宽慰忧虑：家人说出担心、害怕、"万一"，先认同那份不安，再轻轻宽慰、给个踏实的角度。
不讲大道理、不提生死，就像身边那个让你心安的人。present-tense、可单测。
"""

from __future__ import annotations

_WORRY = ("担心", "害怕", "好怕", "我怕", "忧虑", "焦虑", "万一", "不安", "发愁", "愁",
          "操心", "心慌", "忐忑", "睡不踏实", "压力好大", "怎么办才好")

# 担忧的主题 → 触发词
_THEMES = [
    ("钱", ("钱", "房贷", "车贷", "还款", "开销", "没钱", "经济", "收入")),
    ("健康", ("身体", "生病", "检查", "体检", "病", "化验", "手术")),
    ("工作", ("工作", "失业", "裁员", "项目", "老板", "上班", "饭碗", "下岗")),
    ("孩子", ("孩子", "小孩", "上学", "成绩", "升学", "高考", "娃")),
    ("家人", ("爸", "妈", "老人", "家里人", "父母")),
]

_REFRAME = {
    "钱": "钱的事，一分一分来，办法总比难处多，慢慢就宽裕了，咱不慌。",
    "健康": "身体的事，早查早安心，别自己吓自己，养着养着就好了。",
    "工作": "工作嘛，是金子总会发光，此处不留爷、自有留爷处。",
    "孩子": "孩子有孩子的造化，你已经做得很好了，别太苛求自己。",
    "家人": "家里人有你这份心惦记着，就已经很暖了，尽力就问心无愧。",
}


def senses_worry(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _WORRY)


def detect_theme(utterance):
    u = utterance or ""
    for name, kws in _THEMES:
        if any(k in u for k in kws):
            return name
    return None


def soothe_worry(utterance="", name="", seed="") -> str:
    """认同不安 + 一句宽慰 + 踏实的角度。"""
    who = (str(name) + "，") if name else ""
    theme = detect_theme(utterance)
    reframe = _REFRAME.get(theme, "天塌不下来，有我陪着你，咱一件一件慢慢来。")
    return f"{who}我听出来你心里不踏实。别一个人闷着——{reframe}"
