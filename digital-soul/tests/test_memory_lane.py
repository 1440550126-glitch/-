"""一起回忆测试。可直接运行：python tests/test_memory_lane.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.memory_lane import is_recall_invite, recollect  # noqa: E402


def test_is_recall_invite():
    assert is_recall_invite("你还记得那次旅行吗")
    assert is_recall_invite("想想以前的日子")
    assert not is_recall_invite("把灯打开")


def test_recollect():
    r = recollect(["我们一起去海边看日出", "你给我织过一条围巾"], person="小婷", seed="x")
    assert ("海边" in r or "围巾" in r) and "小婷" in r
    assert any(lead in r for lead in ("还记得", "我常想起", "说起来", "一直记着"))


def test_recollect_empty():
    assert recollect([], person="小明") == ""
    assert recollect(None) == ""


def test_recollect_deterministic():
    mems = ["往事一", "往事二", "往事三"]
    assert recollect(mems, seed="k") == recollect(mems, seed="k")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ memory_lane: all tests passed")
