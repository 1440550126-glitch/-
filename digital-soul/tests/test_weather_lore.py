"""看天识天测试。可直接运行：python tests/test_weather_lore.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.weather_lore import (  # noqa: E402
    find_sign,
    is_weather_lore_query,
    lore_for,
    random_lore,
    signs,
)


def test_signs():
    s = signs()
    assert "朝霞" in s and "燕子低飞" in s and "蚂蚁搬家" in s


def test_lore_for():
    assert "朝霞不出门" in lore_for("早上朝霞满天")
    assert "燕子低飞要下雨" in lore_for("燕子飞得低")        # 别名
    assert "蚂蚁搬家" in lore_for("看见蚂蚁搬家")
    assert lore_for("今天开会") == ""


def test_lore_has_meaning():
    s = lore_for("月晕")
    assert "（" in s and "）" in s


def test_find_sign_longest():
    assert find_sign("燕子低飞是不是要下雨") == "燕子低飞"


def test_random_lore():
    r = random_lore(seed="x")
    assert r and "（" in r


def test_is_weather_lore_query():
    assert is_weather_lore_query("讲个天气谚语")
    assert is_weather_lore_query("燕子低飞是要下雨吗")
    assert is_weather_lore_query("教我看天")
    assert not is_weather_lore_query("今天几号")


def test_config_add():
    cfg = {"weather_lore": {"炊烟不升": ["炊烟不升要下雨。", "烟压着不往上飘，多半要变天。"]}}
    assert "炊烟不升要下雨" in lore_for("炊烟不升", cfg)
    assert "炊烟不升" in signs(cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ weather_lore: all tests passed")
