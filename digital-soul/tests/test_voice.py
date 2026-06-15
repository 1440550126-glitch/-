"""语音情感合成测试。可直接运行：python tests/test_voice.py"""

import contextlib
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.voice import Mouth, emotion_to_voice  # noqa: E402


def test_emotion_to_voice_mapping():
    assert emotion_to_voice("喜")["rate"] > emotion_to_voice("哀")["rate"]     # 高兴说得更快
    assert emotion_to_voice("哀")["volume"] < emotion_to_voice("喜")["volume"]  # 低落说得更轻
    assert emotion_to_voice("爱")["tone"] == "温柔"
    assert emotion_to_voice(None)["tone"] == "" and emotion_to_voice(None)["rate"] == 200


def test_mouth_print_fallback_carries_tone():
    m = Mouth()
    if m.available:          # 装了 pyttsx3 就跳过打印断言（无法捕获音频）
        return
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.speak("你好", mood="哀")
    assert "低落" in buf.getvalue()


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ voice: all tests passed")
