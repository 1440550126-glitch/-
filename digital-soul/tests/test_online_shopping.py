"""网购帮手测试。可直接运行：python tests/test_online_shopping.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.online_shopping import (  # noqa: E402
    count, find_topic, general, how_to, is_shopping_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("挑商品", "看评价", "下单付款", "退换货", "防坑"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("网上怎么付款") == "下单付款"
    assert find_topic("七天无理由怎么退") == "退换货"
    assert find_topic("怎么看差评") == "看评价"
    assert find_topic("今天天气好") is None


def test_how_to_has_steps_and_tip():
    s = how_to("下单付款")
    assert "购物车" in s and "货到付款" in s and "提醒" in s
    assert how_to("不存在") == ""


def test_refund_warns_scam():
    s = how_to("退换货")
    assert "App 里走" in s and ("微信" in s or "诈骗" in s)   # 退款防骗


def test_general_has_antiscam():
    g = general()
    assert "货到付款" in g and ("太便宜" in g or "加微信" in g)


def test_is_query_gating():
    assert is_shopping_query("网购怎么弄")
    assert is_shopping_query("网上买东西怎么付款")
    assert is_shopping_query("网购安全吗")
    assert not is_shopping_query("今天天气好")
    assert not is_shopping_query("我网购了个东西")          # 陈述、没问怎么弄 → 不抢


def test_config_extra_topic():
    cfg = {"online_shopping": {"topics": {"比价": ["用比价插件或多平台搜同款", "别只看一家"]}}}
    assert "比价" in topics(cfg)
    assert how_to("比价", cfg).startswith("网购·比价：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ online_shopping: all tests passed")
