"""对对子测试。可直接运行：python tests/test_couplets.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.couplets import is_couplet, opposite, respond  # noqa: E402


def test_opposite_bidirectional():
    assert opposite("天") == "地" and opposite("地") == "天"
    assert opposite("明月") == "清风"
    assert opposite("没这字") is None


def test_is_couplet():
    assert is_couplet("天对什么")
    assert is_couplet("来对个对子")
    assert not is_couplet("今天几号")


def test_respond_pairs():
    assert respond("天对什么") == "天对地。"
    assert respond("山对啥") == "山对水。"
    assert "来对对看" in respond("飞机对什么")            # 没收录的让你来对


def test_respond_sample():
    s = respond("来对个对子")
    assert "对" in s and len(s) > 4


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ couplets: all tests passed")
