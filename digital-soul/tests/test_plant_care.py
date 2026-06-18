"""养花测试。可直接运行：python tests/test_plant_care.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.plant_care import PlantBook  # noqa: E402


def _book(seed=None):
    return PlantBook(pathlib.Path(tempfile.mkdtemp()) / "p.json", seed=seed)


SEED = {"plants": [{"name": "君子兰", "water_every_days": 3},
                   {"name": "绿萝", "water_every_days": 2}]}


def test_seed_and_describe():
    b = _book(SEED)
    assert "君子兰" in b.describe() and "绿萝" in b.describe()


def test_due_when_never_watered():
    b = _book(SEED)
    assert set(b.due(datetime(2026, 6, 18))) == {"君子兰", "绿萝"}


def test_water_then_due_after_cycle():
    b = _book(SEED)
    b.water("君子兰", datetime(2026, 6, 18))
    assert "君子兰" not in b.due(datetime(2026, 6, 19))      # 才浇过，没到点
    assert "君子兰" in b.due(datetime(2026, 6, 21))          # 满 3 天又该浇


def test_reminders():
    b = _book(SEED)
    b.water("君子兰", datetime(2026, 6, 18))
    b.water("绿萝", datetime(2026, 6, 18))
    assert b.reminders(datetime(2026, 6, 18)) == ""          # 都浇过了
    r = b.reminders(datetime(2026, 6, 21))
    assert "浇水" in r and "君子兰" in r


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "p.json"
    PlantBook(p, seed=SEED).water("绿萝", datetime(2026, 6, 18))
    assert PlantBook(p)._find("绿萝")["last"] == "2026-06-18"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ plant_care: all tests passed")
