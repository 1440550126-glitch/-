"""声音相册测试。可直接运行：python tests/test_voicebank.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.voicebank import (  # noqa: E402
    VoiceBank,
    describe,
    is_voicebank_request,
    normalize_clip,
    play_clip,
)

_CLIPS = [
    {"file": "voices/morning.wav", "text": "早睡早起，别熬夜啊",
     "occasions": ["greeting", "morning"], "mood": "关切", "tags": ["叮嘱"]},
    {"file": "voices/laugh.wav", "text": "（爽朗地笑）",
     "occasions": ["happy"], "mood": "喜", "tags": ["笑声"]},
    {"text": "想我了就听听这段", "occasions": ["comfort"], "mood": "爱", "tags": ["想念"]},
]


def test_normalize_str_and_dict():
    a = normalize_clip("就一句话")
    assert a["text"] == "就一句话" and a["occasions"] == []
    b = normalize_clip({"text": "x", "occasion": "greeting", "tags": "叮嘱"})
    assert b["occasions"] == ["greeting"] and b["tags"] == ["叮嘱"]


def test_len_and_from_config():
    vb = VoiceBank.from_config({"voicebank": _CLIPS})
    assert len(vb) == 3
    assert len(VoiceBank.from_config({})) == 0


def test_pick_by_occasion():
    vb = VoiceBank(_CLIPS)
    c = vb.pick(occasion="morning")
    assert "早睡早起" in c["text"]


def test_pick_by_mood():
    vb = VoiceBank(_CLIPS)
    c = vb.pick(mood="喜")
    assert c["tags"] == ["笑声"]


def test_pick_by_keyword():
    vb = VoiceBank(_CLIPS)
    c = vb.pick(keyword="想我")
    assert "想我了" in c["text"]


def test_pick_no_criteria_rotates():
    vb = VoiceBank(_CLIPS)
    assert vb.pick(seed="aa") in vb.all()


def test_pick_unmatched_falls_back():
    vb = VoiceBank(_CLIPS)
    assert vb.pick(occasion="不存在", seed="a") is not None


def test_pick_empty_bank_none():
    assert VoiceBank([]).pick(occasion="x") is None


def test_search_and_for_occasion():
    vb = VoiceBank(_CLIPS)
    assert len(vb.for_occasion("greeting")) == 1
    assert vb.search("熬夜")[0]["file"].endswith("morning.wav")


def test_describe():
    assert "早睡早起" in describe({"text": "早睡早起"})
    assert describe(None) == ""


def test_play_clip_needs_file_and_player():
    # 没文件 → False
    assert play_clip({"text": "x"}) is False
    # 有文件但播放器缺 → False
    assert play_clip({"file": "a.wav"}, which=lambda p: None, exists=lambda p: True) is False
    # 文件不存在 → False
    assert play_clip({"file": "a.wav"}, which=lambda p: "/usr/bin/" + p,
                     exists=lambda p: False) is False
    # 文件在、播放器在 → 跑命令、True
    ran = []
    ok = play_clip({"file": "a.wav"},
                   runner=lambda *a, **k: ran.append(a[0]),
                   which=lambda p: "/usr/bin/" + p if p == "afplay" else None,
                   exists=lambda p: True)
    assert ok is True and ran and ran[0][-1] == "a.wav"


def test_is_voicebank_request():
    assert is_voicebank_request("想听你的声音")
    assert is_voicebank_request("放段你说的话")
    assert is_voicebank_request("听听他说")
    assert not is_voicebank_request("今天天气怎么样")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ voicebank: all tests passed")
