"""量词测试。可直接运行：python tests/test_measure_words.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.measure_words import find_noun, is_measure_query, measure_of  # noqa: E402


def test_measure_of():
    assert "条" in measure_of("鱼")
    assert "匹" in measure_of("马")
    assert "头" in measure_of("牛")
    assert measure_of("钻石") == ""


def test_find_noun_alias_longest():
    assert find_noun("大象用什么量词") == "象"          # 别名
    assert find_noun("马路怎么数") == "马路"            # 长词优先于"马"
    assert find_noun("今天天气") == ""


def test_measure_from_sentence():
    s = measure_of("一什么马")
    assert "匹" in s


def test_is_measure_query():
    assert is_measure_query("鱼用什么量词")
    assert is_measure_query("一什么牛")
    assert is_measure_query("马怎么数")
    assert not is_measure_query("今天几号")
    assert not is_measure_query("我钓了条鱼")            # 没问量词


def test_config_add():
    cfg = {"measure_words": {"骏马": ["匹", "一匹骏马"]}}
    assert "匹" in measure_of("骏马用什么量词", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ measure_words: all tests passed")
