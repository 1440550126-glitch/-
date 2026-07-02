"""防走失测试。可直接运行：python tests/test_anti_wander.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.anti_wander import (  # noqa: E402
    find_topic, is_wander_query, prevent_advice, prevent_all, prevent_topics,
    wants_after, what_to_do,
)


def test_prevent_topics_present():
    ts = prevent_topics()
    for k in ("信息卡", "黄手环定位", "告知邻里", "留近照"):
        assert k in ts
    assert len(ts) >= 5


def test_find_topic_alias():
    assert find_topic("黄手环有用吗") == "黄手环定位"
    assert find_topic("给老人做平安卡") == "信息卡"
    assert find_topic("今天天气好") is None


def test_prevent_advice():
    s = prevent_advice("信息卡")
    assert "姓名" in s and "电话" in s
    assert prevent_advice("不存在") == ""


def test_what_to_do_report_now():
    s = what_to_do()
    assert "110" in s and "24" in s and "监控" in s    # 立刻报警、不等24h、查监控


def test_prevent_all_overview():
    o = prevent_all()
    assert "信息卡" in o and "定位" in o


def test_is_wander_query_gating():
    assert is_wander_query("怎么防老人走失")
    assert is_wander_query("黄手环怎么用")
    assert is_wander_query("老人走失了怎么办")
    assert not is_wander_query("今天天气好")
    assert not is_wander_query("我迷路了")             # 当事人现场 → 归 lost_help，不抢


def test_wants_after():
    assert wants_after("老人走失了怎么办")
    assert not wants_after("怎么防走失")               # 这是预防，不是已走失


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ anti_wander: all tests passed")
