"""节气养生测试。可直接运行：python tests/test_tcm_wellness.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.tcm_wellness import (  # noqa: E402
    food_for, is_wellness_query, season_of, wellness,
)


def test_season_of():
    assert season_of(4) == "春" and season_of(7) == "夏"
    assert season_of(10) == "秋" and season_of(12) == "冬"


def test_wellness():
    s = wellness("秋")
    assert "秋养肺" in s and "梨" in s
    assert "夏养心" in wellness("夏")
    assert wellness("无") == ""


def test_food_for():
    assert "羊肉" in food_for("冬")
    assert food_for("无") == []


def test_is_wellness_query():
    assert is_wellness_query("这季节怎么养生")
    assert is_wellness_query("该补补身子了")
    assert not is_wellness_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ tcm_wellness: all tests passed")
