"""夸夸 / 肯定测试。可直接运行：python tests/test_praise.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.praise import detect_trait, is_praise_request, praise  # noqa: E402


def test_detect_trait():
    assert detect_trait("我今天回家看了爸妈") == "孝顺"
    assert detect_trait("加班到半夜好累") == "努力"
    assert detect_trait("把这事搞定了") == "能干"
    assert detect_trait("今天天气不错") is None


def test_praise_tailored():
    p = praise("我回去陪妈妈了", name="小明")
    assert p.startswith("小明，") and ("孝心" in p or "上心" in p)
    assert "韧劲" in praise("我坚持下来了") or "本事" in praise("我坚持下来了")


def test_praise_generic():
    p = praise("随便说点", name="小婷")
    assert p.startswith("小婷，") and ("很好" in p or "很棒" in p or "够好" in p)


def test_is_praise_request():
    assert is_praise_request("夸夸我")
    assert is_praise_request("我是不是很棒")
    assert not is_praise_request("帮我关灯")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ praise: all tests passed")
