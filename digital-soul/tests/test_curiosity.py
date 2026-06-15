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
    assert qs and "陶艺" in qs[0][0]                       # 把陌生事物变成提问
    assert qs[0][1]                                        # 带回对应的词


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


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ curiosity: all tests passed")
