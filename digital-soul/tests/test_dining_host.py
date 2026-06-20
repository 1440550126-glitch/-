"""点菜请客帮手测试。可直接运行：python tests/test_dining_host.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dining_host import (  # noqa: E402
    advice, count, find_topic, is_dining_query, suggest_dish_count, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("点几个菜", "荤素搭配", "敬酒", "买单结账", "在家待客"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("怎么敬酒不劝酒") == "敬酒"
    assert find_topic("谁付钱合适") == "买单结账"
    assert find_topic("客人来家怎么招待") == "在家待客"
    assert find_topic("今天天气好") is None


def test_suggest_dish_count():
    s = suggest_dish_count(6)
    assert "6" in s and ("8" in s) and "荤" in s and "素" in s and "忌口" in s
    assert suggest_dish_count(0) == ""
    assert suggest_dish_count("x") == ""


def test_advice_toast_no_forcing():
    s = advice("敬酒")
    assert "长辈" in s and ("不强劝" in s or "量力" in s)


def test_advice_bill_graceful():
    s = advice("买单结账")
    assert "悄悄" in s or "别当众" in s


def test_is_query_gating():
    assert is_dining_query("六个人点几个菜")
    assert is_dining_query("点菜怎么搭配")
    assert is_dining_query("敬酒有什么讲究")
    assert not is_dining_query("今天天气好")
    assert not is_dining_query("我去吃饭了")          # 陈述、不是问点菜 → 不抢


def test_config_extra_topic():
    cfg = {"dining_host": {"topics": {"座次": ["主宾坐上座、面对门", "主人靠门便于招呼"]}}}
    assert "座次" in topics(cfg)
    assert "上座" in advice("座次", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dining_host: all tests passed")
