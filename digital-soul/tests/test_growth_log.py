"""成长记录测试。可直接运行：python tests/test_growth_log.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.growth_log import GrowthLog, detect_milestone  # noqa: E402


def _g():
    return GrowthLog(pathlib.Path(tempfile.mkdtemp()) / "g.json")


def test_detect_milestone():
    assert detect_milestone("小宝今天会走路了")
    assert detect_milestone("掉了第一颗牙")
    assert detect_milestone("运动会得了第一名")
    assert not detect_milestone("今天天气真好")


def test_record_and_for_child():
    g = _g()
    g.record("小宝", "第一次叫爷爷", when="2024-01-01")
    g.record("小宝", "会走路了", when="2024-06-01")
    g.record("小花", "上学了", when="2024-09-01")
    assert g.record("", "空") is None
    assert len(g.for_child("小宝")) == 2


def test_timeline_sorted():
    g = _g()
    g.record("小宝", "会走路", when="2024-06-01")
    g.record("小宝", "第一次叫爷爷", when="2024-01-01")
    tl = [it["milestone"] for it in g.timeline("小宝")]
    assert tl == ["第一次叫爷爷", "会走路"]               # 按日期升序


def test_describe_and_recall():
    g = _g()
    g.record("小宝", "第一次叫爷爷", when="2024-01-01")
    d = g.describe("小宝")
    assert "小宝这一路" in d and "第一次叫爷爷" in d
    r = g.recall("小宝")
    assert "一点点长大" in r and "第一次叫爷爷" in r
    assert g.recall("没记过的娃") == ""


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "g.json"
    GrowthLog(p).record("小宝", "会跑了")
    assert len(GrowthLog(p).for_child("小宝")) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ growth_log: all tests passed")
