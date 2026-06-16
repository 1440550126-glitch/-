"""守护提醒测试。可直接运行：python tests/test_guardian.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.guardian import due_reminders  # noqa: E402

CARE = {
    "妈": {"medicine": ["08:00", "20:00"], "checkup": "11-15", "note": "降压药"},
    "爸": {"medicine": "21:30", "note": "护心的药"},
}


def test_medicine_time_match():
    msgs = due_reminders(CARE, datetime(2026, 6, 16, 8, 0))
    assert any("妈" in m and "降压药" in m for m in msgs)
    assert not any("爸" in m for m in msgs)        # 爸不到点


def test_medicine_default_note():
    care = {"奶奶": {"medicine": "07:00"}}
    msgs = due_reminders(care, datetime(2026, 6, 16, 7, 0))
    assert msgs and "药" in msgs[0]                 # 没填 note 时默认"药"


def test_checkup_date_match():
    msgs = due_reminders(CARE, datetime(2026, 11, 15, 9, 0))
    assert any("妈" in m and "复查" in m for m in msgs)


def test_nothing_due():
    assert due_reminders(CARE, datetime(2026, 6, 16, 10, 0)) == []
    assert due_reminders(None, datetime(2026, 6, 16, 8, 0)) == []


def test_bad_config_ignored():
    assert due_reminders({"x": "不是字典"}, datetime(2026, 6, 16, 8, 0)) == []


def test_agent_due_care_dedupes_same_day():
    a = object.__new__(Agent)
    a.care = CARE
    a._care_fired = set()
    now = datetime(2026, 6, 16, 8, 0)
    first = a.due_care(now)
    assert first and any("妈" in m for m in first)
    assert a.due_care(now) == []                    # 同一天同一条不再重复念


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ guardian: all tests passed")
