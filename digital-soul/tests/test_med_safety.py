"""服药常识测试。可直接运行：python tests/test_med_safety.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.med_safety import (  # noqa: E402
    advise, count, find_topic, is_med_safety_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("饭前饭后", "漏服", "能否掰开", "用什么送服", "吃药忌口", "别擅自停药"):
        assert k in ts
    assert count() >= 7


def test_find_topic_alias():
    assert find_topic("忘了吃药怎么办") == "漏服"
    assert find_topic("药能掰开吗") == "能否掰开"
    assert find_topic("吃药能喝酒吗") == "吃药忌口"
    assert find_topic("今天天气好") is None


def test_advise_has_disclaimer():
    s = advise("能否掰开")
    assert "缓释" in s and "说明书" in s                     # 含要点 + 免责
    assert advise("不存在") == ""


def test_grapefruit_and_alcohol_warnings():
    assert "西柚" in advise("用什么送服")
    s = advise("吃药忌口")
    assert "酒" in s and "头孢" in s                         # 头孢配酒的警示


def test_missed_dose_no_double():
    s = advise("漏服")
    assert "双倍" in s and "别" in s                         # 别一次吃双倍


def test_dont_stop_chronic():
    s = advise("别擅自停药")
    assert "慢" in s and ("别自己停" in s or "听医生" in s)


def test_is_query_gating():
    assert is_med_safety_query("这药饭前还是饭后吃")
    assert is_med_safety_query("药能掰开吗")
    assert is_med_safety_query("吃药能喝酒吗")
    assert not is_med_safety_query("今天天气好")
    assert not is_med_safety_query("我吃过药了")             # 打卡 → 归用药守护，不抢


def test_config_extra_topic():
    cfg = {"med_safety": {"topics": {"漏打胰岛素": ["按医嘱补，别自行加量", "拿不准问内分泌科"]}}}
    assert "漏打胰岛素" in topics(cfg)
    assert "医嘱" in advise("漏打胰岛素", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ med_safety: all tests passed")
