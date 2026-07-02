"""解闷测试。可直接运行：python tests/test_boredom.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.boredom import senses_boredom, suggest  # noqa: E402


def test_senses_boredom():
    assert senses_boredom("好无聊啊")
    assert senses_boredom("闲得慌")
    assert not senses_boredom("今天好充实")


def test_suggest_nonempty():
    assert suggest(seed="x")


def test_suggest_night_no_outdoor():
    # 夜里不撺掇出门
    for s in ("a", "b", "c", "d", "e", "f", "g", "h"):
        assert "出去" not in suggest(seed=s, tod="深夜")


def test_suggest_deterministic():
    assert suggest(seed="k") == suggest(seed="k")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ boredom: all tests passed")
