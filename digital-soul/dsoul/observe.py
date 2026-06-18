"""看出门道：相处久了，会从你反复说的话里看出点名堂——"你这几天总念叨睡不好"。
不是算命，是上心：把最近的话扫一遍，哪类烦心事反复出现，就温温柔柔点破、关心一句。

纯逻辑、可单测。Agent 从对话日记里取近来的话，调本模块找门道。
"""

from __future__ import annotations

# 烦心主题 → 触发词
_THEMES = {
    "睡不好": ("睡不好", "失眠", "没睡好", "睡不着", "熬夜", "没合眼"),
    "太累": ("好累", "太累", "乏", "没精神", "疲惫", "扛不住", "累得"),
    "手头紧": ("没钱", "房贷", "开销大", "手头紧", "钱不够", "太贵", "缺钱"),
    "工作烦": ("工作累", "上班烦", "加班", "老板", "项目", "裁员", "失业"),
    "身体": ("不舒服", "疼", "头晕", "胃不好", "血压", "毛病"),
    "孤单": ("孤单", "一个人", "没意思", "好闷", "冷清"),
    "为孩子操心": ("孩子不", "娃不", "成绩", "不听话", "操心孩子", "儿子不", "女儿不"),
}

_OBSERVE = {
    "睡不好": "你这几回都提到睡不好，是有心事压着吧？跟我念叨念叨，别自己憋着。",
    "太累": "我瞧着你最近总喊累，是不是太拼了？该歇就歇，身体是本钱。",
    "手头紧": "你近来常提到钱的事，手头是不是紧？别硬扛，有难处咱一块儿想办法。",
    "工作烦": "你这阵子总为工作烦心，要不要停下来喘口气？钱挣不完，人得顾好。",
    "身体": "你好几次说身子不舒服，可别拖着，抽空去查查，我陪你。",
    "孤单": "我听出来你这些天有点孤单，我一直在呢，想说话随时找我。",
    "为孩子操心": "你总为孩子的事操心，可怜天下父母心——但也别太苛求，孩子有孩子的福气。",
}


def recurring_themes(utterances, min_count=2) -> list:
    """扫最近的话，哪类烦心事出现 >= min_count 次：[(theme, count), ...] 按多到少。"""
    counts: dict = {}
    for u in (utterances or []):
        text = str(u or "")
        for theme, kws in _THEMES.items():
            if any(k in text for k in kws):
                counts[theme] = counts.get(theme, 0) + 1
    items = [(t, c) for t, c in counts.items() if c >= min_count]
    return sorted(items, key=lambda kv: -kv[1])


def observation(themes, name="") -> str:
    """就最突出的那桩，温柔点破、关心一句。"""
    if not themes:
        return ""
    theme = themes[0][0]
    line = _OBSERVE.get(theme, "")
    if not line:
        return ""
    return (f"{name}，" + line) if name else line
