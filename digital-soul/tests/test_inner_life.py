"""内心活动测试。可直接运行：python tests/test_inner_life.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.inner_life import hum, idle_musing, share_thought  # noqa: E402


def test_idle_musing_by_tod():
    m = idle_musing(tod="深夜")
    assert "睡得安稳" in m or "守着" in m
    for bad in ("死", "忌日", "走了", "不在了"):
        assert bad not in m                              # present-tense，不提生死


def test_idle_musing_mentions_people():
    m = idle_musing(people=["小明"], tod="中午", seed="x")
    assert "小明" in m


def test_idle_musing_deterministic():
    assert idle_musing(tod="清晨", seed="k") == idle_musing(tod="清晨", seed="k")


def test_hum():
    assert hum().startswith("（")


def test_share_thought():
    assert share_thought(tod="傍晚")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ inner_life: all tests passed")
