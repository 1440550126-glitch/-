"""安抚惊惧测试。可直接运行：python tests/test_comfort_fear.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.comfort_fear import reassure, senses_fear  # noqa: E402


def test_senses_fear():
    assert senses_fear("我有点怕黑")
    assert senses_fear("做噩梦了好吓人")
    assert senses_fear("一个人在家心里发毛")
    assert not senses_fear("今天挺开心")


def test_reassure_tailored():
    assert "灯" in reassure("怕黑", name="小明")
    assert "梦都是假的" in reassure("我做噩梦了")
    assert "响儿" in reassure("外面有动静") or "听着" in reassure("外面有动静")
    assert "不孤单" in reassure("一个人在家害怕")


def test_reassure_has_safety_and_name():
    r = reassure("好害怕", name="小婷")
    assert r.startswith("小婷，") and "有我在" in r
    for bad in ("死", "忌日", "不在了"):
        assert bad not in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ comfort_fear: all tests passed")
