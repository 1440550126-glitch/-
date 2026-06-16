"""传统节日测试。可直接运行：python tests/test_festival.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.festival import (customs, festival_on, greeting,  # noqa: E402
                            is_memorial_day, today_line)


def test_solar_festivals():
    assert festival_on(datetime(2026, 1, 1)) == "元旦"
    assert festival_on(datetime(2026, 4, 5)) == "清明"
    assert festival_on(datetime(2026, 10, 1)) == "国庆节"
    assert festival_on(datetime(2026, 3, 17)) is None


def test_nth_sunday_mother_father():
    # 2026 年 5 月第二个周日 = 5/10；6 月第三个周日 = 6/21
    assert festival_on(datetime(2026, 5, 10)) == "母亲节"
    assert festival_on(datetime(2026, 6, 21)) == "父亲节"
    assert festival_on(datetime(2026, 5, 3)) is None


def test_greeting_customs_memorial():
    assert "清明" in greeting("清明") or "想念" in greeting("清明")
    assert "扫墓" in customs("清明")
    assert is_memorial_day("清明") and not is_memorial_day("国庆节")


def test_today_line():
    assert "清明" in today_line(datetime(2026, 4, 5))
    assert today_line(datetime(2026, 3, 17)) == ""


def test_agent_festival_methods():
    a = object.__new__(Agent)
    assert "清明" in a.festival_today(datetime(2026, 4, 5))
    assert "粽子" in a.festival_info("端午有什么讲究")
    assert a.festival_info("没有这个节") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ festival: all tests passed")
