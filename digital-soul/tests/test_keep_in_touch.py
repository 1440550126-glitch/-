"""常联系测试。可直接运行：python tests/test_keep_in_touch.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.keep_in_touch import TouchLog  # noqa: E402


def _log(seed=None):
    return TouchLog(pathlib.Path(tempfile.mkdtemp()) / "t.json", seed=seed)


SEED = {"people": [{"name": "小芳", "relation": "闺女", "every_days": 7},
                   {"name": "老战友", "every_days": 30}]}


def test_seed_and_describe():
    b = _log(SEED)
    assert "闺女" in b.describe()


def test_overdue_when_never():
    b = _log(SEED)
    od = dict(b.overdue(datetime(2026, 6, 18)))
    assert "小芳" in od and od["小芳"] is None


def test_touched_then_not_overdue():
    b = _log(SEED)
    assert b.touched("给闺女打电话了", datetime(2026, 6, 18)) == "小芳"
    od = [n for n, _ in b.overdue(datetime(2026, 6, 20))]
    assert "小芳" not in od                              # 才联系过
    od2 = [n for n, _ in b.overdue(datetime(2026, 6, 26))]
    assert "小芳" in od2                                 # 满 7 天又该联系


def test_reminders():
    b = _log(SEED)
    b.touched("小芳", datetime(2026, 6, 1))
    r = b.reminders(datetime(2026, 6, 20))
    assert "闺女小芳" in r and "没联系" in r


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "t.json"
    TouchLog(p, seed=SEED).touched("小芳", datetime(2026, 6, 18))
    assert TouchLog(p).people["小芳"]["last"] == "2026-06-18"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ keep_in_touch: all tests passed")
