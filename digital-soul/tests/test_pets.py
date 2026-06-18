"""养宠测试。可直接运行：python tests/test_pets.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.pets import PetBook  # noqa: E402


def _b(seed=None):
    return PetBook(pathlib.Path(tempfile.mkdtemp()) / "p.json", seed=seed)


SEED = {"pets": [{"name": "旺财", "kind": "狗", "feed_times": ["08:00", "18:00"], "walk": True},
                 {"name": "咪咪", "kind": "猫", "feed_times": ["09:00"]}]}


def test_seed_and_describe():
    b = _b(SEED)
    assert "旺财（狗）" in b.describe() and "咪咪（猫）" in b.describe()


def test_due_feeding_and_fed():
    b = _b(SEED)
    morning = datetime(2026, 6, 18, 8, 10)
    assert "旺财" in b.due_feeding(morning)
    b.fed("旺财", morning)
    assert "旺财" not in b.due_feeding(morning)          # 喂过这顿就不再催


def test_walk_tracking():
    b = _b(SEED)
    now = datetime(2026, 6, 18, 9, 0)
    assert b.needs_walk("旺财", now)                      # 还没遛
    b.walked("旺财", now)
    assert not b.needs_walk("旺财", now)
    assert not b.needs_walk("咪咪", now)                  # 猫不用遛


def test_reminders():
    b = _b(SEED)
    r = b.reminders(datetime(2026, 6, 18, 8, 5))
    assert "喂旺财" in r and "遛旺财" in r


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "p.json"
    PetBook(p, seed=SEED).fed("咪咪", datetime(2026, 6, 18, 9, 0))
    assert PetBook(p)._fed_count("咪咪", "2026-06-18") == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ pets: all tests passed")
