"""克隆嗓音包装脚本测试。可直接运行：python tests/test_say_clone.py

纯逻辑：命令拼装、播放器选择、合成成败判定——都不碰真模型/真音频。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scripts.say_clone import (  # noqa: E402
    build_synth_cmd,
    gpt_sovits_url,
    play_cmd,
    say,
    synthesize,
)


def _which_only(*names):
    """造一个假的 which：只认 names 里的程序。"""
    have = set(names)
    return lambda p: ("/usr/bin/" + p) if p in have else None


def test_gpt_sovits_url_escapes_chinese():
    u = gpt_sovits_url("你好")
    assert u.startswith("http://127.0.0.1:9880/?text=")
    assert "%E4" in u                       # 中文被转义
    assert "text_language=zh" in u


def test_build_synth_cmd_gpt_sovits():
    cmd = build_synth_cmd("gpt-sovits", "你回来啦", out="/tmp/x.wav")
    assert cmd[0] == "curl"
    assert "/tmp/x.wav" in cmd
    assert any("9880" in c for c in cmd)


def test_build_synth_cmd_cosyvoice_with_ref():
    cmd = build_synth_cmd("cosyvoice", "妈做了你爱吃的", ref="voices/mom.wav", out="/tmp/y.wav")
    assert "--prompt" in cmd and "voices/mom.wav" in cmd
    assert "--text" in cmd and "妈做了你爱吃的" in cmd
    assert "/tmp/y.wav" in cmd


def test_build_synth_cmd_fish_without_ref():
    cmd = build_synth_cmd("fish", "外面冷不冷")
    assert cmd[0] == "fish-speech"
    assert "--prompt" not in cmd and "--reference" not in cmd   # 没给 ref 就不带


def test_build_synth_cmd_system_is_none():
    assert build_synth_cmd("system", "随便") is None
    assert build_synth_cmd("", "随便") is None
    assert build_synth_cmd("不存在的引擎", "随便") is None


def test_play_cmd_prefers_afplay():
    cmd = play_cmd("/tmp/a.wav", which=_which_only("afplay", "aplay"))
    assert cmd[0].endswith("afplay") and cmd[-1] == "/tmp/a.wav"


def test_play_cmd_ffplay_gets_quiet_flags():
    cmd = play_cmd("/tmp/a.wav", which=_which_only("ffplay"))
    assert cmd[0].endswith("ffplay")
    assert "-autoexit" in cmd and "-nodisp" in cmd


def test_play_cmd_none_when_no_player():
    assert play_cmd("/tmp/a.wav", which=lambda p: None) is None


def test_synthesize_false_when_binary_missing():
    calls = []
    ok = synthesize("gpt-sovits", "嗨", out="/tmp/z.wav",
                    runner=lambda *a, **k: calls.append(a),
                    which=lambda p: None)            # curl 不存在
    assert ok is False
    assert calls == []                               # 没装就根本不跑


def test_synthesize_runs_and_checks_output():
    ran = []
    ok = synthesize("gpt-sovits", "嗨", out="/tmp/z.wav",
                    runner=lambda *a, **k: ran.append(a[0]),
                    which=_which_only("curl"),
                    exists=lambda p: True)           # 假装产出了 wav
    assert ok is True
    assert ran and ran[0][0] == "curl"


def test_synthesize_false_when_no_output_file():
    ok = synthesize("gpt-sovits", "嗨", out="/tmp/z.wav",
                    runner=lambda *a, **k: None,
                    which=_which_only("curl"),
                    exists=lambda p: False)          # 跑了但没产出
    assert ok is False


def test_synthesize_system_engine_is_false():
    ok = synthesize("system", "嗨", which=_which_only("curl"), exists=lambda p: True)
    assert ok is False                               # system 不走合成


def test_say_falls_back_to_system_when_engine_unset():
    # engine=system → 不合成 → 兜底（不该抛异常，返回 'fallback'）
    assert say("外面冷不冷", engine="system") == "fallback"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ say_clone: all tests passed")
