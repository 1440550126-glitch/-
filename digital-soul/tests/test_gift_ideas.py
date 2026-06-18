"""送礼参考测试。可直接运行：python tests/test_gift_ideas.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.gift_ideas import detect_occasion, gift_ideas  # noqa: E402


def test_by_relation():
    assert "茶" in gift_ideas(relation="父亲") or "酒" in gift_ideas(relation="父亲")
    assert "丝巾" in gift_ideas(relation="母亲")
    assert "合影" in gift_ideas(relation="老伴") or "出去走" in gift_ideas(relation="老伴")


def test_likes_take_priority():
    g = gift_ideas(relation="父亲", likes=["钓鱼竿"])
    assert g.startswith("要不考虑这几样：钓鱼竿")        # 喜好排在最前


def test_occasion_hint():
    g = gift_ideas(relation="母亲", occasion="生日")
    assert "舍不得买" in g                               # 生日心意提示


def test_unknown_relation_fallback():
    g = gift_ideas(relation="不知道是谁")
    assert "用得上" in g


def test_detect_occasion():
    assert detect_occasion("给我妈过生日送啥") == "生日"
    assert detect_occasion("随便问问") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ gift_ideas: all tests passed")
