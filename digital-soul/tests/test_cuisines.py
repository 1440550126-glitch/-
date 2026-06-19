"""八大菜系测试。可直接运行：python tests/test_cuisines.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.cuisines import (  # noqa: E402
    about,
    cuisines,
    eight_cuisines,
    find_cuisine,
    is_cuisine_query,
)


def test_cuisines_count():
    cs = cuisines()
    assert len(cs) == 8
    for c in ("鲁菜", "川菜", "粤菜", "湘菜"):
        assert c in cs


def test_about():
    assert "麻辣" in about("川菜")
    assert "佛跳墙" in about("闽菜")
    assert about("法国菜") == ""


def test_eight():
    e = eight_cuisines()
    assert "鲁" in e and "川" in e and "徽" in e


def test_find_alias():
    assert find_cuisine("四川菜有什么名菜") == "川菜"   # 别名
    assert find_cuisine("湖南菜特点") == "湘菜"
    assert find_cuisine("今天天气") == ""


def test_about_from_sentence():
    assert "白切鸡" in about("粤菜有什么名菜")


def test_is_cuisine_query():
    assert is_cuisine_query("八大菜系是哪八个")
    assert is_cuisine_query("川菜有什么名菜")
    assert is_cuisine_query("鲁菜特点")
    assert not is_cuisine_query("今天几号")
    assert not is_cuisine_query("我爱吃川菜")            # 没问特点/名菜


def test_config_add():
    cfg = {"cuisines": {"东北菜": ["东北", "量大实在", "锅包肉、小鸡炖蘑菇"]}}
    assert "东北菜" in cuisines(cfg)
    assert "锅包肉" in about("东北菜有什么名菜", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ cuisines: all tests passed")
