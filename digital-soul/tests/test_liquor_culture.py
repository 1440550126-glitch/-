"""酒文化测试。可直接运行：python tests/test_liquor_culture.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.liquor_culture import (  # noqa: E402
    count, find_topic, info, is_liquor_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("白酒香型", "黄酒", "敬酒", "解酒", "适量"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("酱香和浓香区别") == "白酒香型"
    assert find_topic("喝醉了怎么办") == "醉酒照护"
    assert find_topic("绍兴酒怎么喝") == "黄酒"
    assert find_topic("今天天气好") is None


def test_aroma_types():
    s = info("白酒香型")
    assert "酱香" in s and "浓香" in s and "清香" in s


def test_moderation_everywhere():
    # 每条都带节制/安全提醒
    for t in ("白酒香型", "黄酒", "解酒", "适量"):
        assert "伤身" in info(t) or "别贪杯" in info(t) or "头孢" in info(t)


def test_sober_up_myth_and_drunk_care():
    s = info("解酒")
    assert "解酒药" in s and ("多喝" in s or "休息" in s)
    d = info("醉酒照护")
    assert "侧" in d and "120" in d                      # 侧卧防呛、严重送医


def test_is_query_gating():
    assert is_liquor_query("白酒有几种香型")
    assert is_liquor_query("喝多了怎么解酒")
    assert is_liquor_query("喝多少酒合适")
    assert not is_liquor_query("今天天气好")
    assert not is_liquor_query("我喝了点酒")             # 陈述、没问 → 不抢


def test_config_extra_topic():
    cfg = {"liquor_culture": {"topics": {"啤酒": "夏天冰镇着喝爽口，但别贪凉伤胃"}}}
    assert "啤酒" in topics(cfg)
    assert "伤胃" in info("啤酒", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ liquor_culture: all tests passed")
