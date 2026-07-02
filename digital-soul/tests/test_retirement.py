"""退休生活测试。可直接运行：python tests/test_retirement.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.retirement import (  # noqa: E402
    a_idea, areas, count, find_area, is_retirement_query, overview, suggest,
)


def test_areas_present():
    a = areas()
    for k in ("学点新的", "动起来", "老有所为", "走出去", "留点念想"):
        assert k in a
    assert count() >= 6


def test_find_area_alias():
    assert find_area("想上老年大学") == "学点新的"
    assert find_area("退休了去旅游") == "走出去"
    assert find_area("帮忙带孙子") == "带孙有度"
    assert find_area("今天天气好") is None


def test_suggest_has_idea_and_warmth():
    s = suggest("动起来")
    assert "太极" in s or "广场舞" in s
    assert suggest("不存在") == ""


def test_keepsake_area_on_theme():
    # "留点念想"呼应数字分身：写回忆、录话留给家人
    s = suggest("留点念想")
    assert "回忆" in s or "照片" in s or "留给" in s


def test_overview_and_idea():
    assert "老年大学" in overview()
    assert "主意" in a_idea(seed="z")


def test_a_idea_deterministic():
    assert a_idea(seed="same") == a_idea(seed="same")


def test_is_query_gating():
    assert is_retirement_query("退休了干点啥好")
    assert is_retirement_query("退休生活怎么过才充实")
    assert is_retirement_query("退休了好无聊")
    assert not is_retirement_query("今天天气好")
    assert not is_retirement_query("我退休了")          # 陈述、没问干啥 → 不抢


def test_config_extra_area():
    cfg = {"retirement": {"areas": {"养生": ["规律作息、清淡饮食、定期体检", "别熬夜别贪嘴"]}}}
    assert "养生" in areas(cfg)
    assert "作息" in suggest("养生", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ retirement: all tests passed")
