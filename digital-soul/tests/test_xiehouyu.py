"""歇后语测试。可直接运行：python tests/test_xiehouyu.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.xiehouyu import (  # noqa: E402
    answer,
    find_front,
    fronts,
    is_xiehouyu_request,
    quiz,
    random_one,
    tail_of,
)


def test_fronts_nonempty():
    fs = fronts()
    assert "外甥打灯笼" in fs and "泥菩萨过江" in fs


def test_tail_of():
    assert tail_of("竹篮打水") == "一场空"
    assert tail_of("八仙过海") == "各显神通"
    assert tail_of("查无此语") == ""


def test_find_front_in_sentence():
    assert find_front("外甥打灯笼歇后语怎么说") == "外甥打灯笼"
    assert find_front("那句泥菩萨过江，怎么接来着") == "泥菩萨过江"
    assert find_front("随便聊聊") == ""


def test_answer_full_with_meaning():
    s = answer("哑巴吃黄连")
    assert "有苦说不出" in s
    assert "意思是" in s


def test_answer_accepts_sentence():
    s = answer("外甥打灯笼这个歇后语")
    assert "照旧" in s


def test_answer_unknown_empty():
    assert answer("不存在的前半句") == ""


def test_random_one_shape():
    r = random_one(seed="x")
    assert "——" in r


def test_quiz_returns_q_and_a():
    q, a = quiz(seed="八仙")
    assert "接下半句" in q
    assert a and a != q


def test_is_xiehouyu_request():
    assert is_xiehouyu_request("来个歇后语")
    assert is_xiehouyu_request("外甥打灯笼下半句是啥")
    assert is_xiehouyu_request("泥菩萨过江怎么接")
    assert not is_xiehouyu_request("今天几号")


def test_config_can_add():
    cfg = {"xiehouyu": {"我家的歇后语": ["真不错", "自家话"]}}
    assert tail_of("我家的歇后语", cfg) == "真不错"
    assert "自家话" in answer("我家的歇后语", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ xiehouyu: all tests passed")
