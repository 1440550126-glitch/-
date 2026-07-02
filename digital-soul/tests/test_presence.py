"""持续感知状态机测试：进入/离开/去抖。可直接运行：python tests/test_presence.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.presence import PresenceMonitor  # noqa: E402


class _FakePerception:
    available = True


def test_enter_then_leave_after_forget():
    events = []
    m = PresenceMonitor(
        _FakePerception(),
        on_enter=lambda n: events.append(("in", n)),
        on_leave=lambda n: events.append(("out", n)),
        forget_after=5.0,
    )
    m.observe({"小婷"}, now=0)      # 进入
    m.observe({"小婷"}, now=1)      # 仍在，无事件
    m.observe(set(), now=2)         # 暂时消失，未超时
    assert ("out", "小婷") not in events
    m.observe(set(), now=10)        # 超过 forget_after -> 离开
    assert events == [("in", "小婷"), ("out", "小婷")]


def test_no_duplicate_enter():
    seen = []
    m = PresenceMonitor(_FakePerception(), on_enter=lambda n: seen.append(n), forget_after=5)
    m.observe({"A"}, now=0)
    m.observe({"A"}, now=1)
    m.observe({"A"}, now=2)
    assert seen == ["A"]


def test_reenter_within_window_no_second_greet():
    seen = []
    m = PresenceMonitor(_FakePerception(), on_enter=lambda n: seen.append(n), forget_after=5)
    m.observe({"A"}, now=0)
    m.observe(set(), now=1)         # 短暂离开
    m.observe({"A"}, now=2)         # 窗口内回来，不应再次打招呼
    assert seen == ["A"]


def test_multiple_people():
    ins = []
    m = PresenceMonitor(_FakePerception(), on_enter=lambda n: ins.append(n), forget_after=5)
    m.observe({"小婷", "阿强"}, now=0)
    assert set(ins) == {"小婷", "阿强"}


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("PASS", _name)
    print("✅ presence: all tests passed")
