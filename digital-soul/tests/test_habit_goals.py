"""习惯养成陪练测试。可直接运行：python tests/test_habit_goals.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.habit_goals import HabitBook  # noqa: E402


def _book(seed=None):
    return HabitBook(pathlib.Path(tempfile.mkdtemp()) / "h.json", seed=seed)


def test_seed_and_describe():
    b = _book({"habits": [{"name": "早睡", "target": "11点前睡"}, "锻炼"]})
    assert "早睡" in b.describe() and "锻炼" in b.describe()


def test_streak_increments_consecutive():
    b = _book()
    b.add("早睡")
    b.check_in("早睡", datetime(2026, 6, 16))
    b.check_in("早睡", datetime(2026, 6, 17))
    b.check_in("早睡", datetime(2026, 6, 18))
    assert b.streak("早睡") == 3


def test_streak_resets_on_gap():
    b = _book()
    b.check_in("锻炼", datetime(2026, 6, 16))
    b.check_in("锻炼", datetime(2026, 6, 18))            # 隔了一天
    assert b.streak("锻炼") == 1


def test_double_checkin_same_day():
    b = _book()
    b.check_in("喝水", datetime(2026, 6, 18, 9))
    b.check_in("喝水", datetime(2026, 6, 18, 15))        # 同一天再打不加
    assert b.streak("喝水") == 1


def test_done_today_and_pending():
    b = _book({"habits": ["早睡", "锻炼"]})
    b.check_in("早睡", datetime(2026, 6, 18))
    assert b.done_today("早睡", datetime(2026, 6, 18))
    assert b.pending(datetime(2026, 6, 18)) == ["锻炼"]


def test_encourage_milestones():
    b = _book()
    for d in range(11, 18):
        b.check_in("早睡", datetime(2026, 6, d))         # 连续7天
    assert "一周" in b.encourage("早睡")
    assert b.streak("早睡") == 7


def test_fuzzy_name_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "h.json"
    b1 = HabitBook(p)
    b1.add("每天锻炼")
    b1.check_in("锻炼", datetime(2026, 6, 18))           # 模糊匹配到"每天锻炼"
    b2 = HabitBook(p)
    assert b2.streak("每天锻炼") == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ habit_goals: all tests passed")
