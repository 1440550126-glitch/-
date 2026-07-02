"""节日日期测试。可直接运行：python tests/test_festival_dates.py"""

import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.festival_dates import (  # noqa: E402
    canonical,
    days_to_festival,
    describe,
    festival_date,
    known_festivals,
    nudge,
)


def test_known_has_majors():
    ks = known_festivals()
    for f in ("春节", "中秋", "端午", "国庆节", "元旦"):
        assert f in ks


def test_canonical_aliases():
    assert canonical("过年") == "春节"
    assert canonical("月饼节") == "中秋"
    assert canonical("十一") == "国庆节"
    assert canonical("六一") == "儿童节"
    assert canonical("离过年") == "春节"          # 宽松包含
    assert canonical("随便") == ""


def test_festival_date_lookup():
    assert festival_date("春节", 2026) == (2, 17)
    assert festival_date("中秋", 2025) == (10, 6)
    assert festival_date("国庆节", 2027) == (10, 1)   # 固定阳历
    assert festival_date("元旦", 2030) == (1, 1)


def test_days_to_fixed_festival():
    # 2026-09-20 → 国庆 10/1 还有 11 天
    assert days_to_festival("国庆节", date(2026, 9, 20)) == 11


def test_days_to_lunar_festival():
    # 2026-09-20 → 中秋 2026-09-25 还有 5 天
    assert days_to_festival("中秋", date(2026, 9, 20)) == 5


def test_days_rolls_to_next_year():
    # 2026-12-10 → 春节看 2027-02-06
    d = days_to_festival("春节", date(2026, 12, 10))
    assert d == (date(2027, 2, 6) - date(2026, 12, 10)).days


def test_days_today_is_zero():
    # 端午 2026 = 6/19
    assert days_to_festival("端午", date(2026, 6, 19)) == 0


def test_describe():
    s = describe("过年", date(2026, 2, 1))
    assert "春节" in s and "还有" in s and "16" in s
    assert describe("中秋", date(2026, 9, 25)).startswith("就是今天")
    assert describe("不是节日", date(2026, 1, 1)) == ""


def test_unknown_returns_none():
    assert days_to_festival("我生日", date(2026, 1, 1)) is None
    assert festival_date("春节", 2099) is None        # 表外年份


def test_nudge_today_blessing():
    assert nudge("春节", 0).startswith("今儿是春节，")
    assert "新春大吉" in nudge("春节", 0)


def test_nudge_somber_festival_no_blessing():
    # 清明没有欢庆祝福，只轻声提一句
    s = nudge("清明", 0)
    assert "快乐" not in s and "祭扫" in s


def test_nudge_upcoming_within_week():
    s = nudge("中秋", 3)
    assert "还有 3 天就中秋了" in s and "月饼" in s


def test_nudge_too_far_or_invalid_empty():
    assert nudge("春节", 30) == ""
    assert nudge("春节", -1) == ""
    assert nudge("不是节日", 0) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ festival_dates: all tests passed")
