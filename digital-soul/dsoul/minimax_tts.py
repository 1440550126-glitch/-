"""MiniMax 语音合成（T2A v2）：用 MiniMax 的云端嗓音/克隆音色把文字念出来。
MiniMax 不是开源的，是付费云服务，但中文与声音克隆质量很顶，正好接到 voice.tts_cmd。

密钥只从环境变量读（MINIMAX_API_KEY），绝不写进代码或配置、绝不入库。
纯逻辑（拼请求 / 解音频）可单测；真正发请求在 synth()，由 scripts/minimax_say.py 调。
"""

from __future__ import annotations

import os

DEFAULT_HOST = "https://api.minimax.io/v1/t2a_v2"      # 国际站；国内可用 https://api.minimaxi.chat/v1/t2a_v2
DEFAULT_MODEL = "speech-02-hd"
DEFAULT_VOICE = "Chinese (Mandarin)_Warm_Bestie"       # 没配自己的克隆音色时，用个温暖的内置女声


def endpoint(host=None, group_id=None) -> str:
    """合成接口地址；有 GroupId 就拼上（部分账号需要，sk- 新密钥通常不需要）。"""
    url = host or os.environ.get("MINIMAX_TTS_HOST") or DEFAULT_HOST
    gid = group_id if group_id is not None else os.environ.get("MINIMAX_GROUP_ID", "")
    return f"{url}?GroupId={gid}" if gid else url


def build_payload(text, voice_id=None, model=None, fmt="mp3",
                  speed=1.0, vol=1.0, pitch=0, sample_rate=32000) -> dict:
    """拼 T2A v2 的请求体。"""
    return {
        "model": model or os.environ.get("MINIMAX_MODEL") or DEFAULT_MODEL,
        "text": str(text or ""),
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id or os.environ.get("MINIMAX_VOICE_ID") or DEFAULT_VOICE,
            "speed": float(speed), "vol": float(vol), "pitch": int(pitch),
        },
        "audio_setting": {
            "sample_rate": int(sample_rate), "bitrate": 128000,
            "format": fmt, "channel": 1,
        },
    }


def decode_audio(resp: dict) -> bytes:
    """从 T2A 响应里取出音频字节（data.audio 是十六进制字符串）。失败抛异常。"""
    if not isinstance(resp, dict):
        raise ValueError("响应不是 JSON 对象")
    br = resp.get("base_resp") or {}
    if br and br.get("status_code") not in (0, None):
        raise RuntimeError(f"MiniMax 报错 {br.get('status_code')}：{br.get('status_msg')}")
    hexstr = ((resp.get("data") or {}).get("audio")) or ""
    if not hexstr:
        raise RuntimeError("响应里没有 data.audio（检查 voice_id / 余额 / 权限）")
    return bytes.fromhex(hexstr)


def synth(text, api_key=None, voice_id=None, model=None, fmt="mp3",
          timeout=60, opener=None, **kw) -> bytes:
    """调 MiniMax T2A 合成音频，返回音频字节。缺密钥/出错会抛异常（好让上层回落）。"""
    import json
    import urllib.request

    key = api_key or os.environ.get("MINIMAX_API_KEY")
    if not key:
        raise RuntimeError("没有 MINIMAX_API_KEY（请 export 进环境变量，别写进代码/配置）")
    body = json.dumps(build_payload(text, voice_id=voice_id, model=model, fmt=fmt, **kw)).encode("utf-8")
    req = urllib.request.Request(
        endpoint(), data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    op = opener or urllib.request.urlopen
    with op(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return decode_audio(data)
