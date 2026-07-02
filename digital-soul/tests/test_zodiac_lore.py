"""生肖星座详解测试。可直接运行：python tests/test_zodiac_lore.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.zodiac_lore import (  # noqa: E402
    animal_traits,
    animals,
    find_animal,
    find_sign,
    is_zodiac_lore_query,
    sign_traits,
    signs,
)


def test_counts():
    assert len(animals()) == 12 and len(signs()) == 12


def test_animal_traits():
    assert "机灵" in animal_traits("鼠")
    assert "忠诚" in animal_traits("狗")
    assert animal_traits("麒麟") == ""


def test_sign_traits():
    assert "射手座" in sign_traits("射手座")
    assert "顾家" in sign_traits("巨蟹座")
    assert sign_traits("蛇夫座") == ""


def test_find_animal():
    assert find_animal("属狗的人") == "狗"
    assert find_animal("我是属老虎的") == "虎"        # 别名
    assert find_animal("今天天气") == ""


def test_find_sign():
    assert find_sign("天蝎座性格") == "天蝎座"
    assert find_sign("我是天蝎") == "天蝎座"          # 简称
    assert find_sign("今天几号") == ""


def test_is_zodiac_lore_query():
    assert is_zodiac_lore_query("属狗的什么性格")
    assert is_zodiac_lore_query("天蝎座性格特点")
    assert is_zodiac_lore_query("属鼠和属马合不合")
    assert not is_zodiac_lore_query("今天几号")
    assert not is_zodiac_lore_query("我属狗")          # 没问性格相配


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ zodiac_lore: all tests passed")
