"""换季防护测试。可直接运行：python tests/test_seasonal_care.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.seasonal_care import (  # noqa: E402
    advice, count, find_topic, is_seasonal_care_query, season_advice,
    season_of, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("防中暑", "防一氧化碳中毒", "防寒保暖", "防滑摔"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("冬天烧炭取暖危险吗") == "防一氧化碳中毒"
    assert find_topic("夏天注意什么") == "防中暑"
    assert find_topic("结冰路滑") == "防滑摔"
    assert find_topic("今天天气好") is None


def test_co_warning_is_lifesaving():
    s = advice("防一氧化碳中毒")
    assert "通风" in s and "120" in s
    assert "开门窗" in s or "关掉气源" in s         # 中毒了的处置


def test_heatstroke_signs():
    s = advice("防中暑")
    assert "正午" in s and ("不出汗" in s or "头晕" in s)


def test_season_mapping():
    assert season_of(1) == "冬" and season_of(7) == "夏"
    assert season_of(4) == "春" and season_of(10) == "秋"
    a = season_advice("冬")
    assert "防一氧化碳中毒" in a and "防寒保暖" in a


def test_is_query_gating():
    assert is_seasonal_care_query("夏天怎么防中暑")
    assert is_seasonal_care_query("一氧化碳中毒症状")
    assert is_seasonal_care_query("换季注意什么")
    assert not is_seasonal_care_query("今天天气好")
    assert not is_seasonal_care_query("我有点中暑了")     # 报症状、没问怎么防 → 不抢


def test_config_extra_topic():
    cfg = {"seasonal_care": {"topics": {"防蚊虫": ["挂蚊帐、清积水", "被咬肿大发烧要就医"]}}}
    assert "防蚊虫" in topics(cfg)
    assert "蚊帐" in advice("防蚊虫", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ seasonal_care: all tests passed")
