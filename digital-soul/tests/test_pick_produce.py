"""挑食材测试。可直接运行：python tests/test_pick_produce.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.pick_produce import (  # noqa: E402
    find_item,
    is_pick_query,
    items,
    tip_for,
)


def test_items_cover():
    its = items()
    for x in ("西瓜", "鸡蛋", "鱼", "螃蟹"):
        assert x in its


def test_tip_for():
    assert "瓜脐" in tip_for("西瓜") or "拍" in tip_for("西瓜")
    assert "沉" in tip_for("鸡蛋") or "粗糙" in tip_for("鸡蛋")
    assert tip_for("钻石") == ""


def test_find_item_alias_longest():
    assert find_item("西瓜怎么挑") == "西瓜"
    assert find_item("番茄怎么选") == "西红柿"        # 别名
    assert find_item("马铃薯怎么买") == "土豆"
    assert find_item("今天天气") == ""


def test_tip_from_sentence():
    assert "西瓜" in tip_for("西瓜怎么挑甜的")


def test_is_pick_query():
    assert is_pick_query("西瓜怎么挑")
    assert is_pick_query("鸡蛋怎么选新鲜的")
    assert is_pick_query("螃蟹怎么买")
    assert not is_pick_query("今天几号")
    assert not is_pick_query("我买了个西瓜")           # 没问怎么挑


def test_config_add():
    cfg = {"pick_produce": {"荔枝": "外壳鲜红、捏着有弹性、闻着清香的新鲜。"}}
    assert "荔枝" in items(cfg)
    assert "弹性" in tip_for("荔枝怎么挑", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ pick_produce: all tests passed")
