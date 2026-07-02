"""哄孩子测试。可直接运行：python tests/test_soothe_child.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.soothe_child import (  # noqa: E402
    find_situation,
    is_child_soothing,
    situations,
    soothe,
)


def test_situations():
    s = situations()
    for x in ("哭闹", "不吃饭", "不睡觉", "摔倒"):
        assert x in s


def test_soothe():
    assert "抱住" in soothe("孩子一直哭闹怎么办") or "接住情绪" in soothe("孩子一直哭闹怎么办")
    assert "别硬喂" in soothe("娃不吃饭咋办")
    assert "仪式" in soothe("孩子不睡觉")
    assert soothe("造火箭") == ""


def test_find_situation_longest():
    assert find_situation("孩子不吃饭挑食") == "不吃饭"
    assert find_situation("今天天气") == ""


def test_is_child_soothing():
    assert is_child_soothing("孩子一直哭怎么办")
    assert is_child_soothing("娃不吃饭咋办")
    assert is_child_soothing("孙子不睡觉怎么哄")
    assert is_child_soothing("摔倒了怎么办支招")
    assert not is_child_soothing("今天几号")
    assert not is_child_soothing("孩子真可爱")           # 没有求助意图


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ soothe_child: all tests passed")
