"""世界模型测试。可直接运行：python tests/test_worldmodel.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.worldmodel import WorldModel  # noqa: E402


def _wm():
    return WorldModel(tempfile.mktemp(suffix=".json"))


def test_reinforce_grows_confidence_with_ceiling():
    wm = _wm()
    for _ in range(10):
        wm.reinforce("person:小婷", "小婷对你很重要")
    assert wm.confidence("person:小婷") == 1.0              # 反复印证 → 笃定
    assert wm.beliefs["person:小婷"]["support"] <= 6        # support 有上限


def test_weaken_self_corrects():
    wm = _wm()
    for _ in range(6):
        wm.reinforce("topic:篮球", "你很在意篮球")
    assert wm.confidence("topic:篮球") == 1.0
    wm.weaken("topic:篮球", 6)                              # 持续相反信号
    assert wm.confidence("topic:篮球") == 0.5               # 动摇到一半一半（改主意）


def test_top_and_shaky_split():
    wm = _wm()
    for _ in range(6):
        wm.reinforce("a", "笃定的事")
    wm.reinforce("b", "拿不准的事")
    wm.weaken("b", 4)                                       # 1 支持 4 反对 → 0.2
    assert "笃定的事" in [s for _, s in wm.top()]
    assert "拿不准的事" in [s for _, s in wm.shaky()]
    assert "拿不准的事" not in [s for _, s in wm.top()]


def test_persist():
    p = tempfile.mktemp(suffix=".json")
    WorldModel(p).reinforce("k", "一条信念")
    assert WorldModel(p).confidence("k") == 1.0


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ worldmodel: all tests passed")
