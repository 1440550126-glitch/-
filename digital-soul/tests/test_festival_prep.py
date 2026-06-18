"""节日筹备测试。可直接运行：python tests/test_festival_prep.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.festival_prep import (  # noqa: E402
    detect_festival, festivals, is_prep_query, prep_for, prep_text,
)


def test_festivals_and_prep_for():
    assert "春节" in festivals() and "中秋" in festivals()
    assert any("年夜饭" in x for x in prep_for("春节"))
    assert any("月饼" in x for x in prep_for("中秋"))
    assert prep_for("不存在的节") == []


def test_detect_festival():
    assert detect_festival("过年要准备什么") == "春节"
    assert detect_festival("中秋节怎么过") == "中秋"
    assert detect_festival("端午") == "端午"
    assert detect_festival("今天天气") is None


def test_is_prep_query():
    assert is_prep_query("过年准备什么")
    assert is_prep_query("中秋要张罗啥")
    assert not is_prep_query("现在几点")


def test_prep_text():
    t = prep_text("春节")
    assert "春节" in t and "年夜饭" in t
    assert prep_text("瞎写的") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ festival_prep: all tests passed")
