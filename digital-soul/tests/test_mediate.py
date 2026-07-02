"""和事佬测试。可直接运行：python tests/test_mediate.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.mediate import detect_other, mediate, senses_conflict  # noqa: E402


def test_senses_conflict():
    assert senses_conflict("我跟老婆吵架了")
    assert senses_conflict("和孩子闹别扭")
    assert not senses_conflict("今天很顺心")


def test_detect_other():
    assert detect_other("跟老公吵了一架") == "老伴"
    assert detect_other("和儿子吵架") == "孩子"
    assert detect_other("跟我妈拌嘴") == "爸妈"
    assert detect_other("和同事闹矛盾") == "朋友"


def test_mediate_tailored():
    m = mediate("我跟老婆吵架了", name="老张")
    assert m.startswith("老张，") and "消消气" in m
    assert "老夫老妻" in m and "隔夜仇" in m
    assert "孩子大了" in mediate("和女儿吵架了")


def test_mediate_neutral():
    m = mediate("我跟邻居吵了")
    assert "不评谁对谁错" in m and "退一步" in m


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ mediate: all tests passed")
