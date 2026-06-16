"""本地日程本测试。可直接运行：python tests/test_calendar.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.calendar_book import (EventBook, days_until,  # noqa: E402
                                 normalize_date, occurs_on)

NOW = datetime(2026, 6, 16, 9, 0)


def test_normalize_date_forms():
    assert normalize_date("2026-06-16") == "2026-06-16"
    assert normalize_date("6/16") == "06-16"
    assert normalize_date("6月16日") == "06-16"
    assert normalize_date("2026年6月16日") == "2026-06-16"
    assert normalize_date("乱写") is None


def test_occurs_on_full_and_recurring():
    assert occurs_on("2026-06-16", NOW) is True
    assert occurs_on("2025-06-16", NOW) is False          # 全日期不循环
    assert occurs_on("06-16", NOW) is True                # MM-DD 每年循环
    assert occurs_on("06-17", NOW) is False


def test_days_until():
    assert days_until("2026-06-16", NOW) == 0
    assert days_until("2026-06-18", NOW) == 2
    assert days_until("06-18", NOW) == 2
    assert days_until("06-15", NOW) == 364                # 今年已过 → 明年


def test_eventbook_add_today_upcoming_persist():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "cal.json"
        b = EventBook(p)
        assert b.add("外婆生日", "6月16日", kind="生日")["date"] == "06-16"
        assert b.add("复诊", "2026-06-18") is not None
        assert b.add("", "6-20") is None                  # 空标题不收
        assert b.add("坏日期", "乱") is None
        assert b.describe_today(NOW) == ["外婆生日"]
        up = [e["title"] for e in b.upcoming(7, NOW)]
        assert up == ["外婆生日", "复诊"]                   # 按天数排序
        b2 = EventBook(p)                                  # 重载持久化
        assert len(b2.items) == 2


def test_add_dedupes():
    with tempfile.TemporaryDirectory() as d:
        b = EventBook(pathlib.Path(d) / "c.json")
        b.add("约定", "06-16")
        b.add("约定", "06-16")
        assert len(b.items) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ calendar: all tests passed")
