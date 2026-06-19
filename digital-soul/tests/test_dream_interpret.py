"""解梦测试。可直接运行：python tests/test_dream_interpret.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dream_interpret import interpret, is_dream_query  # noqa: E402


def test_is_dream_query():
    assert is_dream_query("梦见蛇是什么意思")
    assert is_dream_query("做梦掉牙啥兆头")
    assert not is_dream_query("梦见蛇了")                 # 没问意思
    assert not is_dream_query("今天天气好")


def test_interpret_known():
    assert "进财" in interpret("梦见一条蛇") or "添喜" in interpret("梦见一条蛇")
    assert "财" in interpret("梦见好多水")
    assert "别太当真" in interpret("梦见火")


def test_interpret_deceased_is_warm():
    r = interpret("梦见过世的亲人了")
    assert "惦记" in r or "想念" in r
    for bad in ("吓", "不祥", "凶"):
        assert bad not in r                              # 往温暖处说，不吓人


def test_interpret_unknown_fallback():
    r = interpret("梦见一个没见过的怪东西")
    assert "日有所思" in r and "宽心" in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dream_interpret: all tests passed")
