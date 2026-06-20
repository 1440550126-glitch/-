"""看懂食品标签测试。可直接运行：python tests/test_food_label.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.food_label import (  # noqa: E402
    count, explain, find_topic, is_label_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("配料表", "营养成分表", "钠含量", "糖含量", "保质期日期"):
        assert k in ts
    assert count() >= 7


def test_find_topic_alias():
    assert find_topic("含盐多少算高") == "钠含量"
    assert find_topic("0蔗糖是真无糖吗") == "糖含量"
    assert find_topic("SC编号是啥") == "生产许可"
    assert find_topic("今天天气好") is None


def test_ingredient_order_explained():
    s = explain("配料表")
    assert "从多到少" in s and ("糖" in s or "油" in s)


def test_sodium_salt_conversion():
    s = explain("钠含量")
    assert "盐" in s and "2.5" in s              # 钠×2.5≈盐


def test_sugar_zero_sucrose_trap():
    s = explain("糖含量")
    assert "0 蔗糖" in s and "不等于无糖" in s


def test_overview():
    o = overview()
    assert "配料表" in o and "保质期" in o and "SC" in o


def test_is_query_gating():
    assert is_label_query("配料表怎么看")
    assert is_label_query("钠多少算高")
    assert is_label_query("怎么看食品标签")
    assert not is_label_query("今天天气好")
    assert not is_label_query("我买了袋饼干")    # 陈述、没问怎么看 → 不抢


def test_config_extra_topic():
    cfg = {"food_label": {"topics": {"反式脂肪": "看到'氢化植物油'就是反式脂肪，少吃"}}}
    assert "反式脂肪" in topics(cfg)
    assert "氢化" in explain("反式脂肪", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ food_label: all tests passed")
