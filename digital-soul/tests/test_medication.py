"""用药守护测试。可直接运行：python tests/test_medication.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.medication import MedBook  # noqa: E402


def _book(seed=None):
    return MedBook(pathlib.Path(tempfile.mkdtemp()) / "med.json", seed=seed)


SEED = {"meds": [{"name": "降压药", "times": ["08:00", "20:00"], "note": "饭后服",
                  "stock": 4, "per_dose": 1}]}


def test_seed_and_describe():
    b = _book(SEED)
    assert b.meds[0]["name"] == "降压药"
    assert "降压药" in b.describe()


def test_due_and_take():
    b = _book(SEED)
    morning = datetime(2026, 6, 18, 8, 10)
    due = b.due(morning)
    assert due and due[0][0] == "降压药"
    b.take("降压药", morning)
    assert b.taken_today("降压药", morning) == 1
    assert b.due(morning) == []                        # 吃过这顿就不再催


def test_refill_alert_and_stock():
    b = _book(SEED)                                     # stock 4 < 5 阈值
    assert b.refill_alerts() == [("降压药", 4)]
    b.take("降压药", datetime(2026, 6, 18, 8, 5))
    assert b.meds[0]["stock"] == 3                      # 扣库存


def test_reminders_combines():
    b = _book(SEED)
    lines = b.reminders(datetime(2026, 6, 18, 20, 5))
    assert any("该吃降压药" in s for s in lines)
    assert any("记得早点去配" in s for s in lines)       # 续药提醒


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "med.json"
    b1 = MedBook(p, seed=SEED)
    b1.take("降压药", datetime(2026, 6, 18, 8, 0))
    b2 = MedBook(p)
    assert b2.taken_today("降压药", datetime(2026, 6, 18, 9, 0)) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ medication: all tests passed")
