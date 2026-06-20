"""节庆食物寓意测试。可直接运行：python tests/test_festive_foods.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.festive_foods import (  # noqa: E402
    count, find_food, foods, is_festive_food_query, meaning, recall,
)


def test_foods_present():
    fs = foods()
    for k in ("年糕", "饺子", "汤圆", "鱼", "长寿面"):
        assert k in fs
    assert count() >= 12


def test_find_food_alias():
    assert find_food("过年吃水饺")[0] == "饺子"
    assert find_food("煮碗寿面")[0] == "长寿面"
    assert find_food("摆盘桔子")[0] == "橘子"
    assert find_food("今天天气好") is None


def test_meaning_has_pun():
    assert "年年高" in meaning("年糕")
    assert "余" in meaning("鱼")                    # 年年有余
    assert meaning("不存在") == ""


def test_recall_opens_topic():
    assert "应景" in recall(seed="y")


def test_is_query_gating():
    assert is_festive_food_query("过年为什么吃年糕")
    assert is_festive_food_query("饺子有什么寓意")
    assert is_festive_food_query("过年吃什么有讲究")
    assert not is_festive_food_query("今天天气好")
    assert not is_festive_food_query("我想吃鱼")      # 想吃、没问寓意 → 不抢


def test_config_extra_food():
    cfg = {"festive_foods": {"items": [["馄饨", ["馄饨"], "形如元宝，冬至吃讨个聚财团圆"]]}}
    assert "馄饨" in foods(cfg)
    assert find_food("冬至吃馄饨", cfg)[0] == "馄饨"
    assert "元宝" in meaning("馄饨", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ festive_foods: all tests passed")
