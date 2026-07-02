"""七情情绪状态测试。可直接运行：python tests/test_emotions.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.emotions import EmotionState  # noqa: E402


def test_feel_raises_level():
    e = EmotionState()
    base = e.levels["喜"]
    e.feel({"喜": 0.5}, now=0)
    assert e.levels["喜"] > base


def test_decay_returns_toward_baseline():
    e = EmotionState(baseline=0.1, decay_per_min=1.0)
    e.feel({"怒": 0.9}, now=0)
    assert e.levels["怒"] > 0.5
    e.mood(now=120)  # 两分钟后应大幅回落
    assert e.levels["怒"] < 0.3


def test_observe_love_for_guarded():
    e = EmotionState()
    who = {"name": "小婷", "guard": True, "obey": True, "known": True}
    e.observe("今天好开心，谢谢你", speaker=who, now=0)
    assert e.levels["爱"] > e.baseline
    assert e.levels["喜"] > e.baseline


def test_dislike_for_blocked():
    e = EmotionState()
    who = {"name": "老钱", "obey": False, "known": True}
    e.observe("过来帮我搬东西", speaker=who, now=0)
    assert e.levels["恶"] > e.baseline


def test_prompt_hint_reflects_dominant():
    e = EmotionState()
    e.feel({"喜": 0.8}, now=0)
    assert "喜" in e.prompt_hint(now=0)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ emotions: all tests passed")
