"""生肖星座测试。可直接运行：python tests/test_zodiac.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.zodiac import (  # noqa: E402
    animal_of, answer, constellation, is_zodiac_query,
)


def test_animal_of():
    assert animal_of(2020) == "鼠"        # 庚子鼠
    assert animal_of(2021) == "牛"
    assert animal_of(1948) == "鼠"
    assert animal_of("x") == ""


def test_constellation():
    assert constellation(3, 8) == "双鱼座"
    assert constellation(1, 1) == "摩羯座"        # 跨年兜底
    assert constellation(1, 20) == "水瓶座"
    assert constellation(12, 25) == "摩羯座"


def test_is_zodiac_query():
    assert is_zodiac_query("1948年属什么")
    assert is_zodiac_query("我是什么星座")
    assert not is_zodiac_query("今天几号")


def test_answer():
    assert "属鼠" in answer("1948年属什么")
    assert "鼠" in answer("二〇二〇年属啥")              # 中文年份
    assert "双鱼座" in answer("3月8号是什么星座")
    assert answer("随便聊聊") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ zodiac: all tests passed")
