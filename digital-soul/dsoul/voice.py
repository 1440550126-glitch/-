"""语音输入输出（可选模块，全部优雅降级）。

- Ears（听）：语音转文字，优先 faster-whisper，其次 openai-whisper；
  都没装则 available=False，由上层改用键盘输入。
- Mouth（说）：文字转语音，优先 pyttsx3（离线）；没装则打印文本。

模型都在本地跑：faster-whisper 的 base 模型 int8 量化后很小，16G 内存绰绰有余。
"""

from __future__ import annotations

# 七情 -> 语音参数（语速 rate / 音量 volume / 语气标签 tone）
_VOICE = {
    "喜": {"rate": 225, "volume": 1.0, "tone": "愉悦"},
    "怒": {"rate": 215, "volume": 1.0, "tone": "不悦"},
    "哀": {"rate": 165, "volume": 0.8, "tone": "低落"},
    "惧": {"rate": 185, "volume": 0.75, "tone": "不安"},
    "爱": {"rate": 190, "volume": 0.95, "tone": "温柔"},
    "恶": {"rate": 195, "volume": 0.85, "tone": "冷淡"},
    "欲": {"rate": 180, "volume": 0.9, "tone": "渴望"},
}


def emotion_to_voice(mood) -> dict:
    """把当前主导情绪映射成语音参数；未知/平静用中性默认。"""
    return _VOICE.get(mood, {"rate": 200, "volume": 1.0, "tone": ""})


# 在"本人嗓音档案"之上，情绪带来的增量（语速 Δ、音量 Δ）
_EMO_DELTA = {
    "喜": (25, 0.0), "怒": (15, 0.0), "哀": (-35, -0.2), "惧": (-15, -0.25),
    "爱": (-10, -0.05), "恶": (-5, -0.15), "欲": (-20, -0.1),
}


def voice_params(profile, mood=None) -> dict:
    """以"本人嗓音档案"为基底（语速/音量/系统嗓音），叠加当下情绪增量。

    profile 形如 {rate:170, volume:0.9, voice:"<系统嗓音id>", tts_cmd:"<外部克隆嗓音命令，含{text}>"}。
    """
    profile = profile or {}
    dr, dv = _EMO_DELTA.get(mood, (0, 0.0))
    return {
        "rate": max(80, min(320, int(profile.get("rate", 200)) + dr)),
        "volume": max(0.3, min(1.0, float(profile.get("volume", 1.0)) + dv)),
        "voice": profile.get("voice"),
        "tts_cmd": profile.get("tts_cmd"),
        "tone": _VOICE.get(mood, {}).get("tone", ""),
    }


class Ears:
    def __init__(self, model_size: str = "base") -> None:
        self.backend: str | None = None
        self._model = None
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self.backend = "faster-whisper"
        except Exception:
            try:
                import whisper

                self._model = whisper.load_model(model_size)
                self.backend = "openai-whisper"
            except Exception:
                self.backend = None

    @property
    def available(self) -> bool:
        return self.backend is not None

    def transcribe(self, audio_path) -> str | None:
        if not self.available:
            return None
        if self.backend == "faster-whisper":
            segments, _ = self._model.transcribe(str(audio_path), language="zh")
            return "".join(s.text for s in segments).strip()
        result = self._model.transcribe(str(audio_path), language="zh")
        return (result.get("text") or "").strip()


class Mouth:
    def __init__(self) -> None:
        self.backend: str | None = None
        self._engine = None
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self.backend = "pyttsx3"
        except Exception:
            self.backend = None

    @property
    def available(self) -> bool:
        return self.backend is not None

    def speak(self, text: str, mood=None, profile=None) -> None:
        """播报。mood 让语速/音量随情绪变化；profile 是"本人嗓音档案"。

        若 profile.tts_cmd 配了外部命令（含 {text}），就交给它——可接你本地的声音克隆 CLI，
        用接近本人的嗓音说话。否则用系统 TTS（pyttsx3），再不行就打印。
        """
        v = voice_params(profile, mood) if profile else emotion_to_voice(mood)
        cmd = v.get("tts_cmd")
        if cmd:
            import subprocess
            try:
                subprocess.run(cmd.replace("{text}", text), shell=True, check=False, timeout=60)
                return
            except Exception:
                pass
        if self.available:
            try:
                self._engine.setProperty("rate", v["rate"])
                self._engine.setProperty("volume", v["volume"])
                if v.get("voice"):
                    self._engine.setProperty("voice", v["voice"])
            except Exception:
                pass
            self._engine.say(text)
            self._engine.runAndWait()
        else:
            tag = f"（语气：{v.get('tone')}）" if v.get("tone") else ""
            print(f"🔊（未装 TTS，用文字代替）{tag}{text}")


def record_wav(seconds: float = 5, samplerate: int = 16000) -> str | None:
    """录一段麦克风音频存成 wav，返回路径。缺 sounddevice 则返回 None。"""
    try:
        import numpy as np  # noqa: F401
        import sounddevice as sd
    except Exception:
        return None
    import tempfile
    import wave

    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    path = tempfile.mktemp(suffix=".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(samplerate)
        w.writeframes(audio.tobytes())
    return path
