"""语音输入输出（可选模块，全部优雅降级）。

- Ears（听）：语音转文字，优先 faster-whisper，其次 openai-whisper；
  都没装则 available=False，由上层改用键盘输入。
- Mouth（说）：文字转语音，优先 pyttsx3（离线）；没装则打印文本。

模型都在本地跑：faster-whisper 的 base 模型 int8 量化后很小，16G 内存绰绰有余。
"""

from __future__ import annotations


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

    def speak(self, text: str) -> None:
        if self.available:
            self._engine.say(text)
            self._engine.runAndWait()
        else:
            print(f"🔊（未装 TTS，用文字代替）{text}")


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
