"""口腔护理测试。可直接运行：python tests/test_dental_care.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dental_care import (  # noqa: E402
    advice, count, find_topic, is_dental_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("刷牙", "假牙护理", "牙龈出血", "洗牙", "牙疼"):
        assert k in ts
    assert count() >= 7


def test_find_topic_alias():
    assert find_topic("义齿怎么护理") == "假牙护理"
    assert find_topic("蛀牙疼") == "牙疼"
    assert find_topic("牙结石多") == "洗牙"
    assert find_topic("今天天气好") is None


def test_brushing_method():
    s = advice("刷牙")
    assert "巴氏" in s and "45" in s and "软毛" in s


def test_denture_no_boiling_water():
    s = advice("假牙护理")
    assert "开水" in s and ("别戴着睡" in s or "摘下" in s)


def test_scaling_myth_busted():
    s = advice("洗牙")
    assert "不是" in s and "松" in s             # 不会把牙洗松


def test_is_query_gating():
    assert is_dental_query("牙怎么刷干净")
    assert is_dental_query("假牙怎么护理")
    assert is_dental_query("洗牙会把牙洗松吗")
    assert not is_dental_query("今天天气好")
    assert not is_dental_query("我牙疼")          # 报症状、没问怎么办 → 不抢（留给导诊/急救）


def test_config_extra_topic():
    cfg = {"dental_care": {"topics": {"窝沟封闭": ["给孩子磨牙做封闭防蛀", "六龄牙最该做"]}}}
    assert "窝沟封闭" in topics(cfg)
    assert "防蛀" in advice("窝沟封闭", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dental_care: all tests passed")
