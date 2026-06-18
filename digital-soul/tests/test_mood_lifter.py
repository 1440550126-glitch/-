"""哄你开心测试。可直接运行：python tests/test_mood_lifter.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.mood_lifter import is_lift_request, lift  # noqa: E402


def test_lift_picks_available():
    s = lift(joke="冰箱比我更想我", joy="孙子来看我了", song="《茉莉花》", call_who="闺女")
    assert "冰箱比我更想我" in s                          # 用了段子
    assert "会过去的" in s                                # 收尾打气
    # 最多挑两样，别全堆
    assert s.count("——") <= 2


def test_lift_fallback_when_nothing():
    s = lift()
    assert "陪我说说话" in s and "有我在" in s


def test_lift_deterministic():
    assert lift(joke="x", seed="k") == lift(joke="x", seed="k")


def test_is_lift_request():
    assert is_lift_request("哄哄我开心")
    assert is_lift_request("我今天心情不好")
    assert not is_lift_request("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ mood_lifter: all tests passed")
