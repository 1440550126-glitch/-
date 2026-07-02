"""历史朝代测试。可直接运行：python tests/test_dynasties.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dynasties import (  # noqa: E402
    about,
    dynasties,
    dynasty_song,
    find_dynasty,
    is_dynasty_query,
    order,
)


def test_song():
    s = dynasty_song()
    assert "夏商与西周" in s and "宋元明清" in s


def test_dynasties_order():
    ds = dynasties()
    assert ds[0] == "夏" and ds[-1] == "清"
    assert "唐" in ds and "汉" in ds
    assert "→" in order()


def test_about():
    assert "秦始皇" in about("秦")
    assert "李白" in about("唐")
    assert about("火星朝") == ""


def test_find_dynasty_alias():
    assert find_dynasty("西汉是什么时候") == "汉"
    assert find_dynasty("北宋介绍") == "宋"
    assert find_dynasty("战国时期") == "春秋战国"
    assert find_dynasty("今天天气") == ""


def test_about_from_sentence():
    assert "郑和" in about("明朝有什么")


def test_is_dynasty_query():
    assert is_dynasty_query("背背朝代歌")
    assert is_dynasty_query("唐朝介绍一下")
    assert is_dynasty_query("历史朝代顺序")
    assert is_dynasty_query("西汉是什么时候")
    assert not is_dynasty_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dynasties: all tests passed")
