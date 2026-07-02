"""好奇心与世界模型测试。可直接运行：python tests/test_curiosity.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.curiosity import QuestionLog, form_questions, novel_terms  # noqa: E402


def test_novel_terms_only_unknown():
    known = "我喜欢打篮球，养了金毛豆豆"
    nt = novel_terms("我最近迷上了潜水和冲浪", known)
    assert any("潜水" in t or "冲浪" in t for t in nt)
    assert all("篮球" not in t for t in nt)               # 已知的不算陌生


def test_form_questions_makes_curious_asks():
    qs = form_questions("我开始学陶艺了", "我喜欢打篮球")
    assert "陶艺" in [x[1] for x in qs]                    # 把陌生事物变成提问
    assert any("陶艺" in q for q, *_ in qs)                # 提问里带上那个词


def test_importance_raises_priority():
    low = form_questions("我学了陶艺", "", importance=0.0)
    high = form_questions("我学了陶艺", "", importance=0.4)
    assert high[0][2] > low[0][2]                          # 越重要优先级越高


def test_questionlog_lifecycle():
    p = tempfile.mktemp(suffix=".json")
    ql = QuestionLog(p)
    ql.add("陶艺", "「陶艺」是什么呀？")
    ql.add("陶艺", "重复的不再加")                          # 同一件事不重复
    assert len(ql.items) == 1 and len(ql.open()) == 1
    assert QuestionLog(p).open()                           # 持久化
    qid = ql.open()[0]["id"]
    ql.mark_asked(qid)
    assert ql.open() == []                                 # 问过即不在待问
    ql.add("书法", "「书法」是什么？")
    assert ql.resolve_known("我开始练书法了") == 1          # 学到了就销账
    assert all(it["term"] != "书法" for it in ql.items)


def test_divergent_forecast_feeds_curiosity():
    import tempfile

    from dsoul.agent import Agent
    from dsoul.curiosity import QuestionLog
    a = object.__new__(Agent)
    a.llm = type("L", (), {"available": False})()
    a.curiosity = QuestionLog(tempfile.mktemp(suffix=".json"))
    a.forecast("会不会成")                                # 含糊问题 → 思路分歧大
    op = a.curiosity.open()
    assert op and op[0]["priority"] >= 0.8               # 分歧 → 高优先好奇


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ curiosity: all tests passed")
