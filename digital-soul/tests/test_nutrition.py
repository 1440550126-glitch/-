"""膳食养生测试。可直接运行：python tests/test_nutrition.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.nutrition import (  # noqa: E402
    find_need,
    food_for,
    is_nutrition_query,
    needs,
)


def test_needs_cover():
    ns = needs()
    for x in ("补钙", "补血", "护眼", "养胃"):
        assert x in ns


def test_food_for():
    assert "牛奶" in food_for("补钙吃什么") or "豆腐" in food_for("补钙吃什么")
    assert "菠菜" in food_for("贫血吃什么补血") or "红枣" in food_for("贫血吃什么补血")
    assert food_for("想长高吃什么") == ""             # 没收录


def test_find_need_longest():
    n = find_need("血糖高吃什么")
    assert n and n["name"] == "降三高"


def test_is_nutrition_query():
    assert is_nutrition_query("补钙吃什么")
    assert is_nutrition_query("护眼吃啥好")
    assert is_nutrition_query("老人吃什么好")
    assert not is_nutrition_query("今天几号")
    assert not is_nutrition_query("我钙片吃完了")        # 没问吃什么补


def test_config_add():
    cfg = {"nutrition": [{"name": "补锌", "keys": ["补锌"], "food": "牡蛎、瘦肉、坚果含锌多。"}]}
    assert "补锌" in needs(cfg)
    assert "牡蛎" in food_for("补锌吃什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ nutrition: all tests passed")
