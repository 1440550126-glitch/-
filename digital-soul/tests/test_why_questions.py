"""十万个为什么测试。可直接运行：python tests/test_why_questions.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.why_questions import (  # noqa: E402
    answer,
    count,
    find_question,
    is_why_query,
)


def test_count():
    assert count() >= 20


def test_answer_common():
    assert "蓝光" in answer("天为什么是蓝的") or "散" in answer("天为什么是蓝的")
    assert "放电" in answer("为什么会打雷") or "闪电" in answer("为什么会打雷")
    assert "细菌" in answer("为什么要刷牙") or "蛀牙" in answer("为什么要刷牙")


def test_answer_unknown_empty():
    assert answer("为什么股票会跌") == ""
    assert answer("今天几号") == ""


def test_find_question_longest():
    # "先看到闪电"应命中专门那条，而不是泛"打雷"
    a = find_question("为什么先看到闪电后听到雷")
    assert "光跑得比声音快" in a


def test_is_why_query():
    assert is_why_query("天为什么是蓝的")
    assert is_why_query("彩虹怎么来的")
    assert is_why_query("鱼为什么不淹死")
    assert not is_why_query("今天几号")


def test_config_add():
    cfg = {"why": [{"keys": ["飞机为什么能飞"], "answer": "机翼让上下气流速度不同，托起飞机。"}]}
    assert "机翼" in answer("飞机为什么能飞", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ why_questions: all tests passed")
