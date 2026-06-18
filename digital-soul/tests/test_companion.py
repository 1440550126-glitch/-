"""陪伴与守护测试。可直接运行：python tests/test_companion.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.companion import (  # noqa: E402
    checkin, comfort, greeting_for, presence_line, senses_down, time_of_day,
    weather_care, wellbeing_nudge,
)


def test_time_of_day():
    assert time_of_day(datetime(2026, 6, 18, 6)) == "清晨"
    assert time_of_day(datetime(2026, 6, 18, 12)) == "中午"
    assert time_of_day(datetime(2026, 6, 18, 18)) == "傍晚"
    assert time_of_day(datetime(2026, 6, 18, 1)) == "深夜"


def test_greeting_present_tense_no_death():
    g = greeting_for(datetime(2026, 6, 18, 7))
    assert "早" in g
    for bad in ("死", "忌日", "走了", "不在了", "遗"):
        assert bad not in g


def test_weather_care():
    assert "加件衣裳" in weather_care("今天降温")
    assert "带把伞" in weather_care("有雨")
    assert "多喝水" in weather_care("高温")
    assert weather_care("") == ""


def test_checkin_combines():
    c = checkin(datetime(2026, 6, 18, 7), weather="降温")
    assert "早" in c and "加件衣裳" in c


def test_wellbeing_nudge():
    assert "午饭" in wellbeing_nudge(datetime(2026, 6, 18, 12))
    assert "早点睡" in wellbeing_nudge(datetime(2026, 6, 18, 1))
    assert wellbeing_nudge(datetime(2026, 6, 18, 10)) == ""   # 上午没有固定提醒


def test_senses_down_and_comfort():
    assert senses_down("今天好累")
    assert senses_down("有点难过")
    assert not senses_down("今天很开心")
    c = comfort("我好累", name="小明")
    assert c.startswith("小明，") and "歇会儿" in c
    assert "陪着你" in comfort("我想哭")
    assert "孤单" not in comfort("我好累")                   # 按语义选对安慰


def test_presence_line():
    assert presence_line() in ("我在呢。", "有我陪着你。", "别怕，我一直都在。",
                               "想说啥就跟我说，我听着。")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ companion: all tests passed")
