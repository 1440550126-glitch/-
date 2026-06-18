"""说与动合一测试。可直接运行：python tests/test_perform.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.perform import beats, perform  # noqa: E402


class _Rec:
    def __init__(self):
        self.calls = []

    def say(self, t):
        self.calls.append(("say", t))

    def gesture(self, name, detail=""):
        self.calls.append(("gesture", name))


def test_beats_split_and_gesture():
    bs = beats("你来啦！记得按时吃药。你想我了吗？", emotion="喜")
    segs = [b[0] for b in bs]
    assert len(bs) == 3
    assert "你来啦！" in segs[0]
    assert bs[0][1][0] == "用力点头"                     # 感叹→用力点头
    assert bs[1][1][0] == "点头叮嘱"                     # "记得按时"→叮嘱
    assert bs[2][1][0] == "微微侧首"                     # 问句→侧首


def test_beats_tender():
    bs = beats("我一直想你。")
    assert bs[0][1][0] == "温柔倾身"                     # 暖处→倾身


def test_beats_empty():
    assert beats("") == []


def test_perform_interleaves_say_and_gesture():
    r = _Rec()
    perform(r, "你来啦！记得吃药。", emotion="爱")
    kinds = [c[0] for c in r.calls]
    # 说一句、动一下，交替来
    assert kinds == ["say", "gesture", "say", "gesture"]


def test_perform_none_safe():
    perform(None, "随便", "喜")          # 没机器人不炸


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ perform: all tests passed")
