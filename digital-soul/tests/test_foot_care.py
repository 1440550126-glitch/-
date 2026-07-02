"""足部护理测试。可直接运行：python tests/test_foot_care.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.foot_care import (  # noqa: E402
    advice, count, find_topic, is_foot_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("泡脚", "脚气", "灰指甲", "糖尿病足", "剪脚指甲"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("足癣怎么治") == "脚气"
    assert find_topic("甲癣怎么办") == "灰指甲"
    assert find_topic("脚跟裂了") == "脚后跟干裂"
    assert find_topic("今天天气好") is None


def test_foot_soak_temp_warning():
    s = advice("泡脚")
    assert "40" in s and ("糖尿病" in s or "烫伤" in s)     # 水温 + 糖尿病人当心


def test_diabetic_foot_redflag():
    s = advice("糖尿病足")
    assert "每天检查" in s and ("别拖" in s or "看医生" in s)


def test_corn_dont_cut_yourself():
    s = advice("鸡眼老茧")
    assert "合脚" in s and ("别自己" in s or "割" in s)


def test_overview():
    o = overview()
    assert "泡脚" in o and "糖尿病" in o


def test_is_query_gating():
    assert is_foot_query("泡脚水温多少度合适")
    assert is_foot_query("脚气怎么治")
    assert is_foot_query("剪脚指甲注意啥")
    assert not is_foot_query("今天天气好")
    assert not is_foot_query("我脚有点痒")             # 报症状、没问怎么办 → 不抢


def test_config_extra_topic():
    cfg = {"foot_care": {"topics": {"脚臭": ["勤洗勤换袜、鞋子晒干、撒点爽身粉", "持续严重查查脚气"]}}}
    assert "脚臭" in topics(cfg)
    assert "袜" in advice("脚臭", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ foot_care: all tests passed")
