"""护眼护耳测试。可直接运行：python tests/test_vision_hearing.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.vision_hearing import (  # noqa: E402
    advice, count, find_topic, is_vh_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("护眼日常", "老花眼", "白内障", "青光眼", "听力下降", "助听器"):
        assert k in ts
    assert count() >= 8


def test_find_topic_alias():
    assert find_topic("耳背了怎么办") == "听力下降"
    assert find_topic("老花镜怎么配") == "老花眼"
    assert find_topic("眼睛雾蒙蒙") == "白内障"
    assert find_topic("今天天气好") is None


def test_glaucoma_is_emergency():
    s = advice("青光眼")
    assert "急诊" in s and ("失明" in s or "别等" in s)


def test_floaters_red_flag():
    s = advice("飞蚊症")
    assert "良性" in s and ("闪光" in s or "黑幕" in s or "视网膜" in s)   # 良性但有红旗


def test_earwax_dont_dig_deep():
    s = advice("掏耳朵")
    assert "棉签" in s and ("别" in s and "深" in s)


def test_is_query_gating():
    assert is_vh_query("怎么护眼")
    assert is_vh_query("白内障是什么症状")
    assert is_vh_query("助听器怎么配")
    assert not is_vh_query("今天天气好")
    assert not is_vh_query("我眼睛有点干")           # 报症状、没问怎么办 → 不抢


def test_config_extra_topic():
    cfg = {"vision_hearing": {"topics": {"护牙": ["早晚刷牙、定期洗牙", "牙龈老出血要看牙医"]}}}
    assert "护牙" in topics(cfg)
    assert "刷牙" in advice("护牙", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ vision_hearing: all tests passed")
