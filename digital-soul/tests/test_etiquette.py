"""人情礼俗测试。可直接运行：python tests/test_etiquette.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.etiquette import (  # noqa: E402
    detect_occasion,
    etiquette_for,
    gift_taboos,
    is_etiquette_query,
    normalize_occasion,
    occasions,
)


def test_occasions():
    for o in ("婚礼", "丧事", "探病", "寿宴"):
        assert o in occasions()


def test_normalize_alias():
    assert normalize_occasion("喜酒") == "婚礼"
    assert normalize_occasion("白事") == "丧事"
    assert normalize_occasion("看病人") == "探病"
    assert normalize_occasion("做寿") == "寿宴"
    assert normalize_occasion("无关") == ""


def test_detect_occasion():
    assert detect_occasion("去喝喜酒要注意什么") == "婚礼"
    assert detect_occasion("奔丧有啥讲究") == "丧事"
    assert detect_occasion("今天天气") == ""


def test_etiquette_for():
    assert "红包" in etiquette_for("婚礼")
    assert "节哀" in etiquette_for("丧事")
    assert "梨" in etiquette_for("探病")              # 探病忌送梨
    assert etiquette_for("无此场合") == ""


def test_gift_taboos():
    t = gift_taboos()
    assert "钟" in t and "梨" in t and "伞" in t


def test_is_etiquette_query():
    assert is_etiquette_query("喝喜酒有啥讲究")
    assert is_etiquette_query("送礼忌讳有哪些")
    assert is_etiquette_query("奔丧要注意什么")
    assert not is_etiquette_query("今天几号")
    # "送什么礼物给妈"是送礼参考，不该当礼俗
    assert not is_etiquette_query("送什么礼物给妈")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ etiquette: all tests passed")
