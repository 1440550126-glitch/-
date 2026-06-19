"""节气百科测试。可直接运行：python tests/test_solar_term_lore.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.solar_term_lore import (  # noqa: E402
    detect_term,
    is_term_lore_query,
    lore,
    terms,
)


def test_terms_count():
    assert len(terms()) == 24
    for t in ("立春", "清明", "夏至", "冬至", "大寒"):
        assert t in terms()


def test_detect_term():
    assert detect_term("清明有什么讲究") == "清明"
    assert detect_term("冬至吃啥") == "冬至"
    assert detect_term("今天天气") == ""


def test_lore_format():
    s = lore("清明")
    assert "清明：" in s
    assert "习俗" in s and "农谚" in s
    assert "青团" in s or "踏青" in s


def test_lore_from_sentence():
    s = lore("立冬有什么讲究")
    assert "饺子" in s or "补冬" in s


def test_lore_unknown_empty():
    assert lore("查无此节气") == ""


def test_is_term_lore_query():
    assert is_term_lore_query("清明吃什么")
    assert is_term_lore_query("大暑要注意啥")
    assert is_term_lore_query("冬至有啥讲究")
    assert not is_term_lore_query("今天几号")
    assert not is_term_lore_query("清明")            # 光报名字、没问讲究，不强答


def test_all_terms_have_full_lore():
    for t in terms():
        s = lore(t)
        assert "习俗" in s and "农谚" in s and len(s) > 15


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ solar_term_lore: all tests passed")
