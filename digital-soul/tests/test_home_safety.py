"""居家安全常识测试。可直接运行：python tests/test_home_safety.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.home_safety import (  # noqa: E402
    categories,
    find_topic,
    is_safety_query,
    tip_for,
)


def test_categories():
    cs = categories()
    for c in ("用电安全", "燃气安全", "防火", "防滑防摔"):
        assert c in cs


def test_tip_for():
    assert "插座" in tip_for("用电要注意什么") or "湿手" in tip_for("用电要注意什么")
    assert "关阀" in tip_for("燃气安全注意啥") or "通风" in tip_for("燃气安全注意啥")
    assert tip_for("怎么造火箭") == ""


def test_find_topic_longest():
    t = find_topic("一氧化碳中毒怎么防")
    assert t and t["name"] == "防一氧化碳"


def test_is_safety_query():
    assert is_safety_query("用电安全要注意什么")
    assert is_safety_query("居家安全常识")
    assert is_safety_query("燃气怎么防泄漏")
    assert not is_safety_query("今天几号")
    assert not is_safety_query("家里来电了")            # 没问安全注意


def test_config_add():
    cfg = {"home_safety": [{"name": "防溺水", "keys": ["溺水"], "tip": "孩子游泳要大人看着。"}]}
    assert "防溺水" in categories(cfg)
    assert "大人看着" in tip_for("溺水怎么防", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ home_safety: all tests passed")
