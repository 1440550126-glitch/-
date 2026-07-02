"""主动牵挂测试。可直接运行：python tests/test_reach_out.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.reach_out import compose, worth_reaching  # noqa: E402


def test_worth_reaching():
    assert not worth_reaching(1)                         # 才一天，不急
    assert worth_reaching(5, concern="睡不好")           # 久没见 + 有心事
    assert worth_reaching(5, warmth=0.7)                 # 久没见 + 关系近
    assert not worth_reaching(5, warmth=0.3)             # 久没见但关系淡、无心事
    assert not worth_reaching(None)


def test_compose_basic():
    s = compose("小明", 5)
    assert "小明" in s and "5天没见" in s and "惦记" in s


def test_compose_with_concern():
    s = compose("小芳", 4, concern="工作烦")
    assert "工作烦" in s and "好些没" in s


def test_compose_fallback_name():
    s = compose("", 3, relation="闺女")
    assert "闺女" in s


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reach_out: all tests passed")
