"""动物叫声测试。可直接运行：python tests/test_animal_sounds.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.animal_sounds import (  # noqa: E402
    animals,
    find_animal,
    is_sound_query,
    sound_of,
)


def test_animals_cover():
    a = animals()
    for x in ("狗", "猫", "牛", "青蛙"):
        assert x in a


def test_sound_of():
    assert "汪汪" in sound_of("狗")
    assert "喵" in sound_of("猫")
    assert "呱" in sound_of("青蛙")
    assert sound_of("恐龙") == ""


def test_find_animal_alias_longest():
    assert find_animal("小狗怎么叫") == "狗"
    assert find_animal("奶牛叫声") == "牛"            # 别名
    assert find_animal("今天天气") == ""


def test_sound_from_sentence():
    assert "汪汪" in sound_of("小狗怎么叫呀")


def test_is_sound_query():
    assert is_sound_query("小狗怎么叫")
    assert is_sound_query("青蛙的叫声")
    assert is_sound_query("牛咋叫")
    assert not is_sound_query("今天几号")
    assert not is_sound_query("我家有只狗")            # 没问叫声


def test_config_add():
    cfg = {"animal_sounds": {"布谷鸟": ["布谷——布谷——", "春天叫，提醒人播种。"]}}
    assert "布谷鸟" in animals(cfg)
    assert "播种" in sound_of("布谷鸟怎么叫", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ animal_sounds: all tests passed")
