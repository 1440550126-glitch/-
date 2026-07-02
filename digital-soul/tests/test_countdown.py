"""倒计时测试。可直接运行：python tests/test_countdown.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.countdown import CountdownBook, days_to, parse_date  # noqa: E402

NOW = datetime(2026, 6, 18)


def _b(seed=None):
    return CountdownBook(pathlib.Path(tempfile.mkdtemp()) / "c.json", seed=seed)


def test_parse_date():
    assert parse_date("2026-10-01") == (10, 1, 2026)
    assert parse_date("10-01") == (10, 1, None)
    assert parse_date("十月一号") == (10, 1, None)
    assert parse_date("乱写") is None


def test_days_to_wraps():
    assert days_to((6, 20, None), NOW) == 2
    # 6-01 已过 → 明年
    assert days_to((6, 1, None), NOW) == 348
    assert days_to((10, 1, 2026), NOW) == 105


def test_book_seed_and_query():
    b = _b({"dates": {"过年": "2027-02-06", "娃高考": "06-07"}})
    assert b.days_for("过年", NOW) == 233
    assert "还有" in b.describe("娃高考", NOW)
    assert "还没记下" in b.describe("不存在", NOW)


def test_book_add_chinese_date():
    b = _b()
    b.add("去旅行", "十月一号")
    assert b.days_for("去旅行", NOW) == 105


def test_upcoming_sorted_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "c.json"
    b = CountdownBook(p)
    b.add("近的", "06-20")
    b.add("远的", "12-25")
    up = b.upcoming(NOW)
    assert [n for n, _ in up] == ["近的", "远的"]
    assert CountdownBook(p).days_for("近的", NOW) == 2     # 持久化


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ countdown: all tests passed")
