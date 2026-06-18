"""周年祭 / 纪念仪式测试。可直接运行：python tests/test_anniversary.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.anniversary import (  # noqa: E402
    anniversaries_today, candle, days_until, ritual_steps, who_of,
)


def test_anniversaries_today_with_years():
    dates = {"忌日": "2019-04-05", "冥诞": "1948-08-12"}
    out = anniversaries_today(dates, datetime(2026, 4, 5))
    assert out == [("忌日", 7)]                           # 2026-2019=7
    assert anniversaries_today(dates, datetime(2026, 6, 1)) == []


def test_anniversaries_today_md_only():
    out = anniversaries_today({"祭日": "08-12"}, datetime(2026, 8, 12))
    assert out == [("祭日", None)]                        # 没填年份，年头为 None


def test_days_until_sorted():
    dates = {"忌日": "2019-04-05", "冥诞": "1948-08-12"}
    out = days_until(dates, datetime(2026, 4, 1), within=30)
    assert out[0][0] == "忌日"
    assert out[0][1] == 4                                 # 4-01 → 4-05 还有 4 天
    assert out[0][2] == 7
    # 远超 30 天的不进
    assert days_until(dates, datetime(2026, 1, 1), within=10) == []


def test_days_until_wraps_to_next_year():
    out = days_until({"冥诞": "1948-01-03"}, datetime(2026, 12, 30), within=10)
    assert out and out[0][0] == "冥诞" and out[0][1] == 4   # 跨年到明年 1-03


def test_who_of():
    assert who_of("张爸的忌日") == "张爸"
    assert who_of("外公冥诞") == "外公"
    assert who_of("结婚纪念日") == ""          # 没有具体的人
    assert who_of("忌日") == ""                # 只有类型、抽不出人
    assert who_of("") == ""


def test_ritual_steps():
    steps = ritual_steps("外公的忌日", "外公", last_words="好好过日子",
                         memories=["外公爱喝两口。", "他总让我别熬夜"], years=7)
    assert any("外公的忌日" in s and "7周年" in s for s in steps)
    assert any("好好过日子" in s for s in steps)
    assert any("心烛" in s for s in steps)
    assert any("外公爱喝两口" in s for s in steps)
    assert any("关于外公" in s for s in steps)


def test_ritual_steps_minimal():
    steps = ritual_steps("结婚纪念日")        # 无 who、无遗言、无回忆也能走完
    assert steps and "结婚纪念日" in steps[0]
    assert any("心烛" in s for s in steps)
    assert all("关于、" not in s for s in steps)   # 没有人时不留下"关于、"的尴尬


def test_candle():
    assert "外婆" in candle("外婆")
    assert "TA" in candle("")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ anniversary: all tests passed")
