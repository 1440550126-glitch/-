"""应急测试。可直接运行：python tests/test_emergency.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.emergency import detect_situation, guide, senses_emergency  # noqa: E402


def test_detect_situation():
    assert detect_situation("我摔倒了起不来") == "摔倒"
    assert detect_situation("胸口疼得厉害") == "胸口"
    assert detect_situation("有点喘不上气") == "喘不上气"
    assert detect_situation("今天挺好") is None


def test_senses_emergency():
    assert senses_emergency("救命")
    assert senses_emergency("我摔倒了")
    assert senses_emergency("好难受")
    assert not senses_emergency("今天天气不错")


def test_guide_tailored_and_calm():
    g = guide("我摔倒了", name="老张", contacts_line="儿子（138）")
    assert g.startswith("老张，") and "别慌" in g
    assert "别急着起身" in g
    assert "儿子（138）" in g                            # 把能找的人报出来


def test_guide_chest_calls_120():
    g = guide("胸口疼")
    assert "120" in g


def test_guide_generic():
    g = guide("我很不舒服")
    assert "别慌" in g and "陪着你" in g


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ emergency: all tests passed")
