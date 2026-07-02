"""看病就诊技巧测试。可直接运行：python tests/test_see_doctor.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.see_doctor import (  # noqa: E402
    advice, count, find_topic, is_see_doctor_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("看病前准备", "怎么跟医生说", "记住医嘱", "复诊", "挂号窍门"):
        assert k in ts
    assert count() >= 5


def test_find_topic_alias():
    assert find_topic("陪老人看病要注意") == "有人陪诊"
    assert find_topic("怎么挂号不排队") == "挂号窍门"
    assert find_topic("复查要带啥") == "复诊"
    assert find_topic("今天天气好") is None


def test_prep_bring_records_and_meds():
    s = advice("看病前准备")
    assert "症状" in s and "药" in s and ("病历" in s or "检查单" in s)


def test_tell_doctor_no_hiding():
    s = advice("怎么跟医生说")
    assert "最难受" in s or "重点" in s
    assert "过敏" in s or "别隐瞒" in s


def test_remember_orders():
    s = advice("记住医嘱")
    assert "记下来" in s and ("复查" in s or "确认" in s)


def test_overview():
    o = overview()
    assert "症状" in o and "医嘱" in o and "复诊" in o


def test_is_query_gating():
    assert is_see_doctor_query("看病前要准备什么")
    assert is_see_doctor_query("怎么跟医生说病情")
    assert is_see_doctor_query("挂号怎么不排队")
    assert not is_see_doctor_query("今天天气好")
    assert not is_see_doctor_query("我去看病了")          # 陈述、没问技巧 → 不抢


def test_config_extra_topic():
    cfg = {"see_doctor": {"topics": {"取报告": ["按单子上的时间地点取，或手机上查电子报告", "看不懂找医生解读"]}}}
    assert "取报告" in topics(cfg)
    assert "电子报告" in advice("取报告", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ see_doctor: all tests passed")
