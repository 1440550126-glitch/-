"""想通一件事测试。可直接运行：python tests/test_reason_through.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.reason_through import (  # noqa: E402
    detect_topic, is_dilemma, reason_through,
)


def test_is_dilemma():
    assert is_dilemma("我该不该辞职")
    assert is_dilemma("这事怎么办才好")
    assert not is_dilemma("今天天气不错")


def test_detect_topic():
    assert detect_topic("我在纠结要不要辞职")[0] == "辞职"
    assert detect_topic("该不该借钱给他")[0] == "借钱"
    assert detect_topic("今天吃什么") is None


def test_reason_shows_both_sides_and_turn():
    r = reason_through("我该不该辞职", seed="aa")        # 偶数长度先想 A 面
    assert "头一个念头" in r and "转念一想" in r          # 有初念、有转念
    assert "辞了图个痛快" in r and "饭碗要紧" in r        # 两面都摆出来
    assert "你自己拿" in r                                # 落定时不替人拿主意


def test_reason_turn_order_flips():
    a = reason_through("要不要辞职", seed="aa")           # 偶
    b = reason_through("要不要辞职", seed="a")            # 奇
    assert a.index("饭碗要紧") != b.index("饭碗要紧")     # 先想哪面会变（会改主意的感觉）


def test_reason_weaves_value_and_memory():
    r = reason_through("该不该创业", value="踏实", memory="当年我冒进吃过亏", mood="担心")
    assert "踏实" in r and "冒进吃过亏" in r and "担心" in r


def test_reason_generic_topic():
    r = reason_through("这事我拿不准")
    assert "凡事都有两面" in r and "你自己拿" in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reason_through: all tests passed")
