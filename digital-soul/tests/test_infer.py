"""推断测试。可直接运行：python tests/test_infer.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.infer import infer  # noqa: E402


def test_sleep_and_tired():
    out = infer({"concerns": ["睡不好", "太累"]})
    assert any("没睡踏实" in c for c in out)


def test_bp_and_dizzy():
    out = infer({"bp_high": True, "symptoms": "这两天老头晕"})
    assert any("血压" in c and "头晕" in c for c in out)


def test_bp_and_med_missed():
    out = infer({"bp_high": True, "med_missed": True})
    assert any("药" in c and "别落下" in c for c in out)


def test_money_and_work():
    out = infer({"concerns": ["手头紧", "工作烦"]})
    assert any("一件一件来" in c for c in out)


def test_empty_signals():
    assert infer({}) == []
    assert infer(None) == []


def test_multiple_conclusions():
    out = infer({"concerns": ["睡不好", "太累"], "bp_high": True, "med_missed": True})
    assert len(out) >= 2                                  # 几条迹象推出几条结论


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ infer: all tests passed")
