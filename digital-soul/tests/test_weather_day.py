"""今天穿什么测试。可直接运行：python tests/test_weather_day.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.weather_day import (  # noqa: E402
    day_advice, dress_advice, extras, umbrella,
)


def test_dress_advice_by_temp():
    assert "羽绒服" in dress_advice(-2)
    assert "毛衣" in dress_advice(8)
    assert "薄外套" in dress_advice(15)
    assert "轻便" in dress_advice(24)
    assert "热" in dress_advice(30)
    assert dress_advice("x") == ""


def test_umbrella():
    assert "带把伞" in umbrella("有雨")
    assert "防滑" in umbrella("下雪")
    assert umbrella("晴") == ""


def test_extras():
    assert "防晒" in extras("大太阳很晒")
    assert "口罩" in extras("今天雾霾重")
    assert extras("晴") == ""


def test_day_advice():
    a = day_advice(5, "下雨")
    assert "毛衣" in a and "带把伞" in a
    assert "照顾好自己" in day_advice(None, None)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ weather_day: all tests passed")
