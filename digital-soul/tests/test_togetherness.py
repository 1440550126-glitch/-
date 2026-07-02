"""作伴测试。可直接运行：python tests/test_togetherness.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.togetherness import (  # noqa: E402
    accompany,
    activities,
    is_accompany_request,
)


def test_activities():
    a = activities()
    assert "喝茶" in a and "散步" in a and "赏月" in a


def test_accompany_specific():
    s = accompany("陪我喝杯茶", name="老张")
    assert s.startswith("老张，")
    assert "沏" in s or "慢慢喝" in s


def test_accompany_alias():
    s = accompany("陪我遛遛弯")
    assert "走" in s or "遛" in s


def test_accompany_sunset():
    s = accompany("陪我看夕阳")
    assert "晚霞" in s


def test_accompany_generic_when_no_activity():
    s = accompany("陪陪我")
    assert "我陪你" in s or "陪着你" in s


def test_accompany_no_name():
    assert not accompany("陪我喝茶").startswith("，")


def test_is_accompany_request():
    assert is_accompany_request("陪我喝杯茶")
    assert is_accompany_request("一起看会儿星星")
    assert is_accompany_request("陪陪我")
    assert is_accompany_request("陪我坐会儿")


def test_not_accompany():
    assert not is_accompany_request("今天天气怎么样")
    assert not is_accompany_request("帮我关灯")           # 没有陪伴意图词
    assert not is_accompany_request("一起多少钱")          # 有"一起"但不是作伴


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ togetherness: all tests passed")
