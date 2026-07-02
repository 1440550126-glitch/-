"""听不明白就问测试。可直接运行：python tests/test_clarify.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.clarify import clarify, is_unclear  # noqa: E402


def test_is_unclear():
    assert is_unclear("嗯")
    assert is_unclear("那个")
    assert is_unclear("  ")
    assert is_unclear("那个事")                          # 含糊指代且短
    assert not is_unclear("我今天去爬山了")              # 说清了事
    assert not is_unclear("几点了")                      # 短但明确


def test_clarify_vague_asks_which():
    c = clarify("那个事")
    assert "哪件事" in c or "具体" in c


def test_clarify_generic():
    c = clarify("嗯")
    assert "听明白" in c or "接着说" in c


def test_clarify_deterministic():
    assert clarify("嗯", seed="x") == clarify("嗯", seed="x")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ clarify: all tests passed")
