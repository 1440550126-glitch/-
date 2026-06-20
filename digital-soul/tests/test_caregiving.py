"""照护卧床老人测试。可直接运行：python tests/test_caregiving.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.caregiving import (  # noqa: E402
    advice, count, find_topic, is_caregiving_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("防褥疮", "喂饭防呛", "防肺炎", "心理陪伴", "照护者歇口气"):
        assert k in ts
    assert count() >= 7


def test_find_topic_alias():
    assert find_topic("怎么防压疮") == "防褥疮"
    assert find_topic("喂饭老呛") == "喂饭防呛"
    assert find_topic("换尿垫") == "大小便护理"
    assert find_topic("今天天气好") is None


def test_pressure_sore_turning():
    s = advice("防褥疮")
    assert "翻身" in s and ("2 小时" in s or "发红" in s)
    assert "医护" in s                                   # 免责


def test_feeding_anti_choke():
    s = advice("喂饭防呛")
    assert "坐" in s and "小口" in s and "120" in s


def test_caregiver_self_care():
    s = advice("照护者歇口气")
    assert "求助" in s or "歇" in s
    # 照护者吐露太累，也认得出来给支持
    assert find_topic("照顾人太累了") == "照护者歇口气"


def test_overview():
    o = overview()
    assert "翻身" in o and "防呛" in o and "照护者" in o


def test_is_query_gating():
    assert is_caregiving_query("卧床老人怎么护理")
    assert is_caregiving_query("怎么防褥疮")
    assert is_caregiving_query("照顾人太累了")
    assert not is_caregiving_query("今天天气好")
    assert not is_caregiving_query("老人睡了")           # 陈述 → 不抢


def test_config_extra_topic():
    cfg = {"caregiving": {"topics": {"防深静脉血栓": ["帮着按摩活动下肢、抬高", "腿肿热痛要就医"]}}}
    assert "防深静脉血栓" in topics(cfg)
    assert "按摩" in advice("防深静脉血栓", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ caregiving: all tests passed")
