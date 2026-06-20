"""隔代教育测试。可直接运行：python tests/test_grandparenting.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.grandparenting import (  # noqa: E402
    advice, count, find_topic, is_grandparenting_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("别太溺爱", "口径一致", "安全第一", "科学带娃", "照顾好自己"):
        assert k in ts
    assert count() >= 5


def test_find_topic_alias():
    assert find_topic("孩子太惯了怎么办") == "别太溺爱"
    assert find_topic("和孩子父母教育分歧") == "口径一致"
    assert find_topic("把屎把尿对吗") == "科学带娃"
    assert find_topic("今天天气好") is None


def test_safety_first():
    s = advice("安全第一")
    assert "防烫" in s or "防摔" in s or "误食" in s


def test_consistency_no_undermine():
    s = advice("口径一致")
    assert "拆台" in s or "护短" in s


def test_caregiver_tired_self_care():
    assert find_topic("带娃太累了") == "照顾好自己"
    s = advice("照顾好自己")
    assert "歇" in s or "分工" in s


def test_overview():
    o = overview()
    assert "规矩" in o and "安全" in o and "口径一致" in o


def test_is_query_gating():
    assert is_grandparenting_query("带孙子要注意什么")
    assert is_grandparenting_query("孩子太溺爱怎么办")
    assert is_grandparenting_query("带娃太累了")
    assert not is_grandparenting_query("今天天气好")
    assert not is_grandparenting_query("我在带孙子")      # 陈述、没问 → 不抢


def test_config_extra_topic():
    cfg = {"grandparenting": {"topics": {"零食有度": ["别拿零食哄、正餐为主", "甜的别多吃护牙"]}}}
    assert "零食有度" in topics(cfg)
    assert "正餐" in advice("零食有度", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ grandparenting: all tests passed")
