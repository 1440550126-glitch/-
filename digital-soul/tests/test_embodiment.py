"""机器身体注入灵魂测试。可直接运行：python tests/test_embodiment.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.embodiment import (  # noqa: E402
    attend, body_language, express, guard_stance, idle,
)


class _Rec:
    """记录机器人收到的动作指令。"""

    def __init__(self):
        self.calls = []

    def say(self, t):
        self.calls.append(("say", t))

    def move(self, d, m=1.0):
        self.calls.append(("move", d, m))

    def look_at(self, t):
        self.calls.append(("look", t))

    def protect(self, t):
        self.calls.append(("protect", t))

    def gesture(self, name, detail=""):
        self.calls.append(("gesture", name))


def test_body_language():
    assert body_language("喜")[0] == "点头前倾"
    assert body_language("哀")[0] == "放缓垂首"
    assert body_language("没这情绪")[0] == "自然站立"     # 默认平和


def test_express_looks_and_gestures():
    r = _Rec()
    express(r, "喜", speaker="小明")
    kinds = [c[0] for c in r.calls]
    assert "look" in kinds and "gesture" in kinds
    assert ("look", "小明") in r.calls


def test_express_sad_approaches():
    r = _Rec()
    express(r, "哀", speaker="小婷")
    assert any(c[0] == "move" for c in r.calls)           # 难过时身体凑近陪着
    r2 = _Rec()
    express(r2, "喜")
    assert not any(c[0] == "move" for c in r2.calls)      # 高兴就不必凑近


def test_attend_and_idle_and_guard():
    r = _Rec()
    attend(r, "小明")
    assert ("look", "小明") in r.calls
    idle(r, seed="x")
    assert any(c[0] == "gesture" for c in r.calls)
    guard_stance(r, "小婷")
    assert ("protect", "小婷") in r.calls


def test_none_robot_safe():
    express(None, "喜", "x")          # 没有机器人也不该炸
    idle(None)
    guard_stance(None, "x")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ embodiment: all tests passed")
