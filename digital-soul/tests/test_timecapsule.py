"""时光胶囊测试。可直接运行：python tests/test_timecapsule.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.timecapsule import CapsuleBook, is_due  # noqa: E402

NOW = datetime(2026, 6, 16, 9, 0)


def test_is_due_full_and_recurring():
    assert is_due("2026-06-16", NOW) is True          # 正是当天
    assert is_due("2026-06-10", NOW) is True          # 错过 → 补送
    assert is_due("2026-12-31", NOW) is False         # 未到
    assert is_due("06-16", NOW) is True               # MM-DD 每年那天
    assert is_due("06-17", NOW) is False


def test_add_due_once_and_speak():
    with tempfile.TemporaryDirectory() as d:
        b = CapsuleBook(pathlib.Path(d) / "cap.json")
        assert b.add("孙女", "2035-06-16", "好好长大") is not None
        assert b.add("", "2026-06-16", "") is None     # 空消息不收
        assert b.add("小明", "乱日期", "x") is None
        b.add("小婷", "2026-06-16", "别太想我")
        due = b.due(NOW)
        assert len(due) == 1 and due[0]["recipient"] == "小婷"
        assert b.due(NOW) == []                        # 只送一次
        assert "别太想我" in CapsuleBook.speak(due[0])


def test_pending_and_persist():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "c.json"
        b = CapsuleBook(p)
        b.add("孙女", "2035-06-16", "等你十八岁")
        assert len(b.pending()) == 1
        assert len(CapsuleBook(p).items) == 1          # 持久化


def test_agent_add_and_due():
    a = object.__new__(Agent)
    with tempfile.TemporaryDirectory() as d:
        a.capsules = CapsuleBook(pathlib.Path(d) / "c.json")
        a.add_capsule("小婷", "2026-06-16", "记得吃饭")
        lines = a.due_capsules(NOW)
        assert lines and "记得吃饭" in lines[0] and "小婷" in lines[0]


def test_agent_no_capsules_safe():
    a = object.__new__(Agent)
    a.capsules = None
    assert a.due_capsules() == [] and a.add_capsule("x", "2030-01-01", "y") is None


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ timecapsule: all tests passed")
