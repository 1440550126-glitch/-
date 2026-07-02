"""老话俗语测试。可直接运行：python tests/test_proverbs.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.proverbs import (  # noqa: E402
    for_theme, match_theme, proverb_for, recite, themes,
)


def test_themes_and_for_theme():
    ts = themes()
    assert "家和" in ts and "健康" in ts
    assert "家和万事兴。" in for_theme("家和")
    assert for_theme("不存在的主题") == []


def test_match_theme():
    assert match_theme("平时要省着点花钱") == "勤俭"
    assert match_theme("多读书有好处") == "读书"
    assert match_theme("身体锻炼很重要") == "健康"
    assert match_theme("今天买了双鞋") is None


def test_proverb_for():
    p = proverb_for("平时要勤俭节约")
    assert p.startswith("老话说得好，") and len(p) > len("老话说得好，")
    assert proverb_for("随便聊聊毫不相关") == ""


def test_proverb_for_deterministic():
    assert proverb_for("锻炼身体", seed="a") == proverb_for("锻炼身体", seed="a")


def test_recite():
    r = recite("健康", k=2)
    assert "健康" in r and "/" in r
    assert recite("不存在").startswith("说到做人")    # 回落到"做人"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ proverbs: all tests passed")
