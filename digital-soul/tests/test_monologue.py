"""内心独白测试。可直接运行：python tests/test_monologue.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.monologue import _MOOD_THOUGHTS, compose_thought  # noqa: E402


def test_association_bubbles_up_first():
    t = compose_thought("聊聊小婷", mood="心情愉悦", assoc=["我和小婷在篮球场认识"], speaker="张明")
    assert "闪过" in t and "小婷" in t                 # 联想优先冒头


def test_dilemma_mood_speaker_fallback():
    assert "打鼓" in compose_thought("该不该", dilemma=True)
    assert "心情愉悦" in compose_thought("x", mood="心情愉悦")
    assert "张明" in compose_thought("x", speaker="张明")
    assert compose_thought("随便", seed=1)             # 兜底也非空


def test_emotional_flavor():
    assert compose_thought("x", mood_char="哀", seed=0) in _MOOD_THOUGHTS["哀"]   # 低落底色
    assert compose_thought("x", mood_char="爱", seed=0) in _MOOD_THOUGHTS["爱"]   # 爱意底色
    # 联想 + 情绪 → 联想带情绪尾音（确定用 [0] 模板）
    t = compose_thought("聊聊", mood_char="哀", assoc=["篮球场认识小婷"])
    assert "闪过" in t and "闷闷" in t


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ monologue: all tests passed")
