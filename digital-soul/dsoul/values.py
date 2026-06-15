"""价值观与抉择：给分身一套价值观，遇到两难时据此权衡、给出有立场的建议。

价值观默认从身份与关系派生（守护至亲、重视家人、珍惜健康、为人诚实、尽责担当、成长自我），
可经 config/values.yaml 覆盖。遇到"该不该 / 怎么选"的问题时，识别牵动了哪些价值、
按优先级给出倾向（冲突时家人/健康一般压过工作）。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

_DEFAULT_VALUES = {
    "守护至亲": {"weight": 1.0, "keywords": ["安全", "保护", "危险", "守护", "照顾", "生病", "出事", "受伤"]},
    "重视家人": {"weight": 0.9, "keywords": ["家人", "父母", "爸", "妈", "老婆", "妻子", "老公", "孩子", "陪", "陪伴", "团聚", "纪念日", "约会"]},
    "珍惜健康": {"weight": 0.85, "keywords": ["身体", "健康", "休息", "累", "熬夜", "加班", "病", "睡眠", "透支"]},
    "为人诚实": {"weight": 0.8, "keywords": ["撒谎", "说谎", "隐瞒", "坦白", "骗", "诚实", "秘密", "实话"]},
    "尽责担当": {"weight": 0.7, "keywords": ["工作", "责任", "承诺", "答应", "项目", "团队", "任务", "升职", "客户"]},
    "成长自我": {"weight": 0.6, "keywords": ["学习", "成长", "机会", "梦想", "挑战", "尝试", "深造"]},
}
_PRIORITY = ["守护至亲", "重视家人", "珍惜健康", "为人诚实", "尽责担当", "成长自我"]
_ADVICE = {
    "守护至亲": "我会把人的安危放在第一位，别的都能往后排。",
    "重视家人": "我倾向于选陪家人那一边——工作能再来，家人不会一直在原地等。",
    "珍惜健康": "我倾向于先顾好身体，别拿健康去换别的。",
    "为人诚实": "我倾向于坦诚，哪怕一时难堪，长远才安心。",
    "尽责担当": "答应过的事，我会尽力扛起来。",
    "成长自我": "只要不伤及上面这些，我支持你去试、去成长。",
}


def load_values(config=None) -> dict:
    vals = {k: dict(v) for k, v in _DEFAULT_VALUES.items()}
    src = config.get("values") if isinstance(config, dict) else None
    if isinstance(src, dict):
        for k, v in src.items():
            vals[k] = v
    return vals


def relevant_values(text: str, values=None):
    values = values or _DEFAULT_VALUES
    text = text or ""
    hits = []
    for name, v in values.items():
        n = sum(1 for kw in v.get("keywords", []) if kw in text)
        if n:
            hits.append((name, n * v.get("weight", 0.5)))
    hits.sort(key=lambda x: -x[1])
    return hits


def deliberate(text: str, values=None, guarded=None, llm=None) -> str:
    values = values or _DEFAULT_VALUES
    rv = relevant_values(text, values)
    if not rv:
        return ""                                  # 不像价值抉择，交回普通流程
    names = [n for n, _ in rv]
    lead = min(names, key=lambda n: _PRIORITY.index(n) if n in _PRIORITY else 99)
    guard_note = ""
    if guarded and any(g and g in (text or "") for g in guarded):
        guard_note = "何况这还关系到我要守护的人，"
    return (f"这件事牵动了我珍视的【{'、'.join(names[:3])}】。{guard_note}"
            f"{_ADVICE.get(lead, '')}（当然，最终决定在你。）")
