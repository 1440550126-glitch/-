"""触景生情测试。可直接运行：python tests/test_reminisce.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.reminisce import reminisce  # noqa: E402


def test_reminisce_uses_memories_and_emotion():
    s = reminisce("老房子", ["小时候在那住", "院里有棵枣树"], emotion="爱")
    assert "老房子" in s and "枣树" in s
    assert "最暖" in s            # 爱 → 暖的引语
    assert s.endswith("我都没忘。")


def test_reminisce_empty_is_graceful():
    s = reminisce("某物", [])
    assert "想不真切" in s and "某物" in s


def test_reminisce_unknown_emotion_default_lead():
    s = reminisce("那年", ["发生了些事"], emotion="未知")
    assert "一桩桩都还清楚" in s


def test_agent_reminisce_about():
    a = object.__new__(Agent)
    a.identity = {"name": "张明", "personality": {}}
    a._recall = lambda q, k=4: [(0.9, {"text": "在篮球场认识小婷", "emotion": "爱"})]
    s = a.reminisce_about("篮球场")
    assert "篮球场" in s and "小婷" in s


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reminisce: all tests passed")
