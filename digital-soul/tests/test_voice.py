"""语音情感合成测试。可直接运行：python tests/test_voice.py"""

import contextlib
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.voice import Mouth, emotion_to_voice, voice_params  # noqa: E402


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


def test_voice_params_persona_plus_emotion():
    prof = {"rate": 160, "volume": 0.9, "voice": "zh-cn"}     # 慢嗓门的外公
    base = voice_params(prof, None)
    assert base["rate"] == 160 and base["voice"] == "zh-cn"
    sad = voice_params(prof, "哀")
    assert sad["rate"] < base["rate"] and sad["volume"] < base["volume"]   # 低落更慢更轻
    happy = voice_params(prof, "喜")
    assert happy["rate"] > base["rate"]                       # 高兴更快
    assert 80 <= sad["rate"] <= 320                           # 有界


def test_external_tts_cmd_invoked():
    import os
    import tempfile
    mark = tempfile.mktemp()
    Mouth().speak("你好", profile={"tts_cmd": f"touch '{mark}'  # {{text}}"})
    assert os.path.exists(mark)                               # 外部克隆嗓音命令被调用
    os.remove(mark)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ voice: all tests passed")
