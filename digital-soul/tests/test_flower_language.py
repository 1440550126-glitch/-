"""花语测试。可直接运行：python tests/test_flower_language.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.flower_language import (  # noqa: E402
    find_flower,
    flowers,
    gift_taboos,
    is_flower_query,
    meaning_of,
    recommend,
)


def test_flowers_cover():
    fs = flowers()
    for f in ("玫瑰", "康乃馨", "百合", "向日葵"):
        assert f in fs


def test_meaning_of():
    assert "爱情" in meaning_of("玫瑰")
    assert "母爱" in meaning_of("康乃馨")
    assert meaning_of("红玫瑰")                       # 别名
    assert meaning_of("塑料花") == ""


def test_recommend_by_occasion():
    assert "康乃馨" in recommend("母亲节送什么花")
    assert "玫瑰" in recommend("送老婆什么花")
    assert "向日葵" in recommend("看病人送什么花")
    assert recommend("随便聊聊") == ""


def test_recommend_known_flower_has_meaning():
    s = recommend("给妈妈送花")
    assert "康乃馨" in s and "花语" in s


def test_gift_taboos():
    t = gift_taboos()
    assert "白菊" in t or "白花" in t
    assert "探病" in t


def test_find_flower():
    assert find_flower("玫瑰代表什么") == "玫瑰"
    assert find_flower("今天几号") == ""


def test_is_flower_query():
    assert is_flower_query("玫瑰花语")
    assert is_flower_query("康乃馨代表什么")
    assert is_flower_query("送什么花给老师")
    assert not is_flower_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ flower_language: all tests passed")
