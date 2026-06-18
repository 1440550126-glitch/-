"""随口提醒测试。可直接运行：python tests/test_reminders.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.reminders import (  # noqa: E402
    ReminderBook, extract_task, is_reminder_request, parse_when,
)

NOW = datetime(2026, 6, 18, 10, 0)


def _b():
    return ReminderBook(pathlib.Path(tempfile.mkdtemp()) / "r.json")


def test_parse_when_relative():
    assert parse_when("半小时后叫我", NOW) == datetime(2026, 6, 18, 10, 30)
    assert parse_when("20分钟后提醒我", NOW) == datetime(2026, 6, 18, 10, 20)
    assert parse_when("2小时后", NOW) == datetime(2026, 6, 18, 12, 0)


def test_parse_when_clock():
    assert parse_when("下午三点", NOW) == datetime(2026, 6, 18, 15, 0)
    assert parse_when("晚上8点半", NOW) == datetime(2026, 6, 18, 20, 30)
    # 早上8点已过 → 顺延到明天
    assert parse_when("8点", NOW) == datetime(2026, 6, 19, 8, 0)
    assert parse_when("明天9点", NOW) == datetime(2026, 6, 19, 9, 0)


def test_extract_task():
    assert extract_task("提醒我下午三点吃药") == "吃药"
    assert extract_task("半小时后叫我关火") == "关火"


def test_is_reminder_request():
    assert is_reminder_request("提醒我吃药")
    assert not is_reminder_request("今天吃什么")


def test_book_add_due_persist():
    b = _b()
    b.parse_and_add("提醒我下午三点吃药", now=NOW)
    assert b.pending() and b.pending()[0]["task"] == "吃药"
    assert b.due(datetime(2026, 6, 18, 14, 59)) == []        # 还没到
    assert b.due(datetime(2026, 6, 18, 15, 0)) == ["吃药"]   # 到点
    assert b.due(datetime(2026, 6, 18, 15, 1)) == []         # 不重复
    p = b.path
    assert ReminderBook(p).pending() == []                   # 已触发，持久化


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reminders: all tests passed")
