"""应季时鲜测试。可直接运行：python tests/test_seasonal_food.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.seasonal_food import (  # noqa: E402
    in_season,
    is_in_season,
    is_seasonal_query,
    season_of,
    whats_fresh,
)


def test_season_of():
    assert season_of(4) == "春"
    assert season_of(7) == "夏"
    assert season_of(10) == "秋"
    assert season_of(1) == "冬"


def test_in_season_lists():
    d = in_season(7)
    assert d["季节"] == "夏"
    assert "西瓜" in d["水果"]
    assert "黄瓜" in d["蔬菜"]


def test_whats_fresh():
    s = whats_fresh(datetime(2026, 7, 15))
    assert "夏天" in s
    assert "西瓜" in s
    assert "天if" not in s and "False" not in s        # 没有残留的笔误


def test_is_in_season():
    assert is_in_season("西瓜", 7)
    assert is_in_season("草莓", 4)
    assert not is_in_season("西瓜", 1)


def test_is_seasonal_query():
    assert is_seasonal_query("现在吃什么水果当季")
    assert is_seasonal_query("有什么应季的菜")
    assert is_seasonal_query("时令的水果有啥")
    assert not is_seasonal_query("今天几号")


def test_in_season_copy():
    d = in_season(7)
    d["水果"].append("乱入")
    assert "乱入" not in in_season(7)["水果"]            # 不污染内部数据


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ seasonal_food: all tests passed")
