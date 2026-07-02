"""生平采访：用一串温和的问题，把一个人的人生一段段问出来——

给"在世时就想留下点什么"的人，或替逝者补全记忆的家人用。答案可直接灌进记忆库
（带上提到的年份），慢慢喂养出更像 TA 的分身。问题库是纯数据，选择逻辑可单测。
"""

from __future__ import annotations

# 按人生阶段组织的引导问题
INTERVIEW = [
    ("童年", [
        "你是哪一年、在哪儿出生的？",
        "小时候家里是什么光景？最记得的一顿饭是什么？",
        "童年最好的玩伴是谁？你们都玩些什么？",
        "有没有一件小时候的事，到现在都还记得清清楚楚？",
    ]),
    ("少年", [
        "上学时你是个什么样的学生？最喜欢哪门课？",
        "少年时谁对你影响最大？TA 教会你什么？",
        "那时候你偷偷许过什么愿望、做过什么梦？",
    ]),
    ("青年", [
        "第一份工作是什么？还记得第一笔工钱怎么花的吗？",
        "你是怎么认识你爱人的？哪一刻动了心？",
        "年轻时最大胆的一次决定是什么？",
    ]),
    ("成家", [
        "成家那天是什么心情？",
        "孩子出生那一刻，你在想什么？",
        "一家人最难忘的一次出门/过年是哪回？",
    ]),
    ("中年", [
        "扛过最重的一段日子是什么时候？怎么扛过来的？",
        "这些年你最自豪的一件事是什么？",
        "有没有谁，你一直想说声谢谢却没说出口？",
    ]),
    ("晚年", [
        "现在的一天，你最喜欢哪个时辰、做什么？",
        "有什么老物件你一直舍不得扔？它有什么故事？",
    ]),
    ("感悟", [
        "回头看，你觉得这辈子最要紧的是什么？",
        "如果只留一句话给后人，你想说什么？",
        "有什么遗憾，或者放下了的事，想说说吗？",
    ]),
]


def all_questions() -> list:
    """拍平成 [(阶段, 问题), …]。"""
    return [(stage, q) for stage, qs in INTERVIEW for q in qs]


def next_question(asked=None) -> tuple | None:
    """下一道没问过的题；都问完返回 None。asked 是已问问题文本的集合/列表。"""
    done = set(asked or [])
    for stage, q in all_questions():
        if q not in done:
            return (stage, q)
    return None


def progress(asked=None) -> float:
    """已问比例（0~1）。"""
    total = len(all_questions())
    if not total:
        return 1.0
    done = len(set(asked or []) & {q for _, q in all_questions()})
    return round(done / total, 3)


def answer_to_memory(answer):
    """把一句回答整理成一条记忆（文本 + 提取到的年份）；空答返回 None。"""
    text = (answer or "").strip()
    if not text:
        return None
    from .annotate import extract_when
    return {"text": text, "when": extract_when(text)}
