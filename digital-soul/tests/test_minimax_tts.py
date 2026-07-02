"""MiniMax 云端 TTS（T2A v2）测试——全程不联网，只验拼装/解码逻辑与回落。
可直接运行：python tests/test_minimax_tts.py"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.minimax_tts import (  # noqa: E402
    DEFAULT_HOST, DEFAULT_MODEL, build_payload, decode_audio, endpoint, synth,
)


def _clear_env():
    for k in ("MINIMAX_API_KEY", "MINIMAX_GROUP_ID", "MINIMAX_TTS_HOST",
              "MINIMAX_VOICE_ID", "MINIMAX_MODEL"):
        os.environ.pop(k, None)


def test_endpoint_default_and_groupid():
    _clear_env()
    assert endpoint() == DEFAULT_HOST                       # 没 GroupId 就是裸地址
    assert endpoint(group_id="g123") == DEFAULT_HOST + "?GroupId=g123"
    os.environ["MINIMAX_GROUP_ID"] = "envg"
    assert endpoint().endswith("?GroupId=envg")             # 从环境变量取
    os.environ["MINIMAX_TTS_HOST"] = "https://api.minimaxi.chat/v1/t2a_v2"
    assert endpoint().startswith("https://api.minimaxi.chat")  # 国内站可切
    _clear_env()


def test_build_payload_shape_and_overrides():
    _clear_env()
    p = build_payload("你好呀")
    assert p["text"] == "你好呀" and p["stream"] is False
    assert p["model"] == DEFAULT_MODEL
    assert p["voice_setting"]["voice_id"]                   # 有个默认音色
    assert p["audio_setting"]["format"] == "mp3"
    # 显式参数能覆盖
    p2 = build_payload("x", voice_id="my_clone", model="speech-01", fmt="wav",
                       speed=1.2, vol=0.8, pitch=2, sample_rate=24000)
    assert p2["voice_setting"]["voice_id"] == "my_clone"
    assert p2["model"] == "speech-01"
    assert p2["audio_setting"]["format"] == "wav"
    assert p2["audio_setting"]["sample_rate"] == 24000
    assert p2["voice_setting"]["speed"] == 1.2 and p2["voice_setting"]["pitch"] == 2
    # 环境变量也能定音色/模型
    os.environ["MINIMAX_VOICE_ID"] = "env_voice"
    assert build_payload("x")["voice_setting"]["voice_id"] == "env_voice"
    _clear_env()


def test_decode_audio_hex_roundtrip():
    raw = b"\x00\x01ID3 fake-mp3 \xff\xfb"
    resp = {"data": {"audio": raw.hex()}, "base_resp": {"status_code": 0}}
    assert decode_audio(resp) == raw                        # 十六进制还原成字节


def test_decode_audio_errors():
    # base_resp 报错要抛
    try:
        decode_audio({"base_resp": {"status_code": 1004, "status_msg": "balance"}})
        assert False, "应当抛异常"
    except RuntimeError as e:
        assert "1004" in str(e)
    # 没音频也要抛（别返回空字节让上层以为成功）
    try:
        decode_audio({"data": {}, "base_resp": {"status_code": 0}})
        assert False, "应当抛异常"
    except RuntimeError:
        pass
    # 不是字典直接抛
    try:
        decode_audio("nope")
        assert False
    except ValueError:
        pass


def test_synth_requires_key():
    _clear_env()
    try:
        synth("你好")                                       # 没 key
        assert False, "缺密钥应当抛异常（好让上层回落）"
    except RuntimeError as e:
        assert "MINIMAX_API_KEY" in str(e)


def test_synth_uses_bearer_and_posts(monkeypatch_env=True):
    _clear_env()
    raw = b"fake-audio-bytes"
    seen = {}

    class FakeResp:
        def __init__(self, payload):
            self._p = payload

        def read(self):
            import json
            return json.dumps(self._p).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_opener(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.headers.get("Authorization")
        seen["method"] = req.get_method()
        seen["body"] = req.data
        return FakeResp({"data": {"audio": raw.hex()}, "base_resp": {"status_code": 0}})

    out = synth("念句话", api_key="sk-test-123", voice_id="vc", opener=fake_opener)
    assert out == raw
    assert seen["auth"] == "Bearer sk-test-123"             # 用 Bearer 鉴权
    assert seen["method"] == "POST"
    assert b"voice_setting" in seen["body"]                 # 请求体带上了
    assert DEFAULT_HOST.split("/v1")[0] in seen["url"]
    _clear_env()


def test_module_never_hardcodes_a_key():
    # 安全红线：源码里不许出现真实密钥前缀（密钥只能来自环境变量）
    src = pathlib.Path(__file__).resolve().parent.parent / "dsoul" / "minimax_tts.py"
    text = src.read_text(encoding="utf-8")
    assert "sk-cp-" not in text and "sk-test" not in text
    assert "os.environ" in text and "MINIMAX_API_KEY" in text


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ minimax_tts: all tests passed")
