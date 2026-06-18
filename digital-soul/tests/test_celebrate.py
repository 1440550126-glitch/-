"""报喜测试。可直接运行：python tests/test_celebrate.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.celebrate import (  # noqa: E402
    celebrate, detect_good_news, milestone_text,
)


def test_detect_good_news():
    assert detect_good_news("我升职了！") == "升职"
    assert detect_good_news("我考上研究生了") == "金榜"
    assert detect_good_news("我们要结婚了") == "喜结良缘"
    assert detect_good_news("宝宝出生了") == "添丁"
    assert detect_good_news("今天下雨") is None


def test_celebrate_tailored():
    c = celebrate("我升职了", name="小婷")
    assert c.startswith("小婷，") and ("努力" in c or "加个菜" in c)
    assert "白头偕老" in celebrate("我们领证了")
    assert celebrate("没什么事") == ""


def test_milestone_text():
    assert milestone_text("升职", "小明") == "小明的喜事：升职。"
    assert "家人" in milestone_text("中奖")
    assert milestone_text(None) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ celebrate: all tests passed")
