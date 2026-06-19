"""十二时辰养生测试。可直接运行：python tests/test_shichen.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.shichen import (  # noqa: E402
    advice_for,
    find_shichen,
    is_shichen_query,
    now_advice,
    shichen_of,
)


def test_shichen_of_basic():
    assert shichen_of(0)[0] == "子时"           # 23-1 跨午夜，0点属子时
    assert shichen_of(23)[0] == "子时"
    assert shichen_of(6)[0] == "卯时"
    assert shichen_of(12)[0] == "午时"
    assert shichen_of(8)[0] == "辰时"


def test_now_advice():
    s = now_advice(datetime(2026, 6, 19, 12, 0))
    assert "午时" in s and "心经" in s
    s2 = now_advice(datetime(2026, 6, 19, 0, 30))
    assert "子时" in s2 and "睡" in s2


def test_find_shichen():
    r = find_shichen("子时该干啥")
    assert r and r[0] == "子时"
    assert find_shichen("今天天气") is None


def test_advice_for():
    assert "胆经" in advice_for("子时养生")
    assert "现在是" in advice_for("现在该养生做点啥")
    assert advice_for("造火箭") == ""


def test_is_shichen_query():
    assert is_shichen_query("十二时辰养生")
    assert is_shichen_query("几点该睡最好")
    assert is_shichen_query("午时养生该干啥")
    assert not is_shichen_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ shichen: all tests passed")
