"""过日子小窍门测试。可直接运行：python tests/test_lifehacks.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.lifehacks import (  # noqa: E402
    categories,
    is_lifehack_query,
    match,
    random_tip,
    tip_for,
    tips_in,
)


def test_categories_cover():
    cs = categories()
    for c in ("清洁", "厨房", "收纳", "省钱", "防潮", "衣物"):
        assert c in cs


def test_tip_for_oil():
    t = tip_for("油烟机油渍怎么去")
    assert "淘米水" in t or "小苏打" in t


def test_tip_for_blood_cold_water():
    t = tip_for("血渍怎么洗掉")
    assert "冷水" in t


def test_tip_for_sweater_shrink():
    t = tip_for("毛衣缩水了怎么办")
    assert "护发素" in t


def test_tip_for_unknown_empty():
    assert tip_for("今天星期几") == ""


def test_match_picks_most_relevant():
    # "洋葱辣眼"应命中切洋葱那条，而不是别的
    h = match("切洋葱总辣眼睛")
    assert h is not None and h["cat"] == "厨房"
    assert "洋葱" in h["tip"] or "辣" in h["tip"]


def test_tips_in_category():
    ts = tips_in("防虫")
    assert any("蚊子" in t for t in ts)
    assert any("蟑螂" in t for t in ts)


def test_random_tip_shape():
    r = random_tip(seed="x")
    assert r.startswith("教你个过日子的小窍门：")


def test_is_lifehack_query():
    assert is_lifehack_query("有什么生活小窍门")
    assert is_lifehack_query("油渍怎么去")
    assert is_lifehack_query("回南天怎么防潮")
    assert is_lifehack_query("毛衣缩水了咋办")
    # 提到关键词但不是求办法 → 不算
    assert not is_lifehack_query("我今天买了瓶醋")
    # 完全无关
    assert not is_lifehack_query("今天天气怎么样")


def test_config_can_add_hack():
    cfg = {"hacks": [{"cat": "自家", "keys": ["腌咸菜"], "tip": "腌咸菜先晾蔫再下盐。"}]}
    assert tip_for("腌咸菜怎么弄", cfg) == "腌咸菜先晾蔫再下盐。"
    assert is_lifehack_query("腌咸菜怎么弄", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ lifehacks: all tests passed")
