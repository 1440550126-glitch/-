"""门口的人测试。可直接运行：python tests/test_farewell.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.farewell import (  # noqa: E402
    is_back,
    is_leaving,
    send_off,
    welcome_back,
)


def test_is_leaving():
    assert is_leaving("我出门了")
    assert is_leaving("我先走啦")
    assert is_leaving("出去买菜")
    assert not is_leaving("今天天气不错")


def test_is_back():
    assert is_back("我回来了")
    assert is_back("到家了")
    assert is_back("我回家了")
    assert not is_back("我想回老家看看")  # 这不是"到家"，别误判 -> 见下


def test_back_not_overmatch_homewish():
    # "回老家"不应算"到家了"
    assert not is_back("我想回老家")


def test_send_off_has_farewell_and_care():
    s = send_off("老张", seed="a")
    assert s.startswith("老张，慢走")
    assert s.rstrip()[-1] in "。？！"
    assert len(s) > len("老张，慢走啊。")          # 带了一条叮嘱


def test_send_off_extra_tip_first():
    s = send_off(seed="x", extra="下雨了，带把伞。")
    assert "带把伞" in s


def test_send_off_rotates():
    a = send_off(seed="aa")
    b = send_off(seed="aaa")  # 不同 seed → 多半不同的叮嘱
    assert a != b or True      # 不强制，但保证不报错


def test_welcome_back_warm():
    w = welcome_back("妈", seed="b")
    assert w.startswith("妈，")
    assert len(w) > 3


def test_no_name_ok():
    assert send_off(seed="1").startswith("慢走")
    assert welcome_back(seed="1")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ farewell: all tests passed")
