"""稳住心神测试。可直接运行：python tests/test_comfort_anxiety.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.comfort_anxiety import (  # noqa: E402
    breathing, calm, grounding, senses_anxiety,
)


def test_senses_anxiety():
    assert senses_anxiety("我心慌得厉害")
    assert senses_anxiety("静不下来，坐立不安")
    assert not senses_anxiety("今天挺平静")
    assert not senses_anxiety("我胸口疼")                 # 急症归 emergency，这里不接


def test_breathing_and_grounding():
    assert "深呼吸" in breathing() and "数四下" in breathing()
    assert "五样东西" in grounding() and "安全的" in grounding()


def test_calm_picks_exercise():
    a = calm("我心慌", name="小明", seed="aa")            # 偶数 → 着地
    assert a.startswith("小明，") and "我在" in a
    assert "五样东西" in a or "深呼吸" in a               # 总会带一个练习


def test_calm_present_no_death():
    for u in ("心慌", "坐立不安"):
        c = calm(u)
        for bad in ("死", "忌日", "不在了"):
            assert bad not in c


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ comfort_anxiety: all tests passed")
