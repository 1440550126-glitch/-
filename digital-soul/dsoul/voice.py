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


def _say_args(text, v):
    """macOS 自带 `say`（中文语音质量好、零安装）。"""
    args = ["say"]
    if v.get("voice"):
        args += ["-v", str(v["voice"])]      # 如 Tingting（普通话女声）/ Sinji
    r = int(v.get("rate") or 180)
    args += ["-r", str(max(90, min(320, r)))]    # 词/分钟，随情绪变
    args.append(text)
    return args


def _espeak_args(prog):
    """Linux 的 espeak-ng / espeak，中文用 -v zh。"""
    def build(text, v):
        r = int(v.get("rate") or 175)
        amp = int((v.get("volume") or 1.0) * 150)
        return [prog, "-v", "zh", "-s", str(max(80, min(320, r))),
                "-a", str(max(0, min(200, amp))), text]
    return build


def detect_system_tts():
    """探测系统自带的语音命令：Mac 用 say，Linux 用 espeak。没有则 None。"""
    import shutil
    if shutil.which("say"):
        return ("say", _say_args)
    for prog in ("espeak-ng", "espeak"):
        if shutil.which(prog):
            return (prog, _espeak_args(prog))
    return None


def render_tts_cmd(cmd, text):
    """把 tts_cmd 模板里的 {text} 安全替换成要说的话（自动转义，防引号/特殊字符出岔）。

    模板里写裸 {text} 即可（不要再套引号），我们会用 shell 安全引用包好；
    也可在命令里用环境变量 $DSOUL_TEXT 取到原文。
    """
    import shlex
    t = str(text or "")
    if "{text}" in str(cmd):
        return str(cmd).replace("{text}", shlex.quote(t))
    return str(cmd)


def run_tts_cmd(cmd, text, runner=None, timeout=120) -> bool:
    """跑外部声音克隆命令把 text 说出来。跑通返回 True；出错/没装/超时返回 False（好让上层回落）。"""
    import os
    import subprocess
    if not cmd:
        return False
    runner = runner or subprocess.run
    env = dict(os.environ, DSOUL_TEXT=str(text or ""))
    try:
        runner(render_tts_cmd(cmd, text), shell=True, check=True, timeout=timeout, env=env)
        return True
    except Exception:
        return False


class Mouth:
    def __init__(self) -> None:
        self.backend: str | None = None
        self._engine = None
        self._syscmd = None
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self.backend = "pyttsx3"
        except Exception:
            self._engine = None
        if self.backend is None:                 # 没装 pyttsx3 就用系统自带 TTS
            self._syscmd = detect_system_tts()
            if self._syscmd:
                self.backend = self._syscmd[0]

    @property
    def available(self) -> bool:
        return self.backend is not None

    def speak(self, text: str, mood=None, profile=None) -> None:
        """播报。mood 让语速/音量随情绪变化；profile 是"本人嗓音档案"。

        优先级：profile.tts_cmd（外部声音克隆 CLI，最像本人）> pyttsx3 >
        系统自带 TTS（Mac 的 say / Linux 的 espeak，零安装就能出声）> 打印文字。
        """
        v = voice_params(profile, mood) if profile else emotion_to_voice(mood)
        cmd = v.get("tts_cmd")
        if cmd:
            if run_tts_cmd(cmd, text):           # 克隆嗓音跑通了就用它
                return
            # 没跑通（命令出错/没装/服务没起）——别哑，回落到下面的引擎
        if self.backend == "pyttsx3" and self._engine is not None:
            try:
                self._engine.setProperty("rate", v["rate"])
                self._engine.setProperty("volume", v["volume"])
                if v.get("voice"):
                    self._engine.setProperty("voice", v["voice"])
            except Exception:
                pass
            self._engine.say(text)
            self._engine.runAndWait()
            return
        if self._syscmd is not None:
            import subprocess
            try:
                subprocess.run(self._syscmd[1](text, v), check=False, timeout=60)
                return
            except Exception:
                pass
        tag = f"（语气：{v.get('tone')}）" if v.get("tone") else ""
        print(f"🔊（没找到语音引擎，用文字代替）{tag}{text}")


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


# ---------- 语音体检：一条条查清楚哪通了、哪没装、怎么补 ----------

_PLAYERS = ("afplay", "aplay", "paplay", "ffplay")


def _has_module(name) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def diagnose(profile=None, which=None, has_module=None):
    """给语音链路做个体检，返回一组 (项目, 通没通, 说明, 没通时怎么补)。

    纯逻辑：靠 which（找命令）和 has_module（查 Python 包）两个探针，便于单测。
    """
    import shutil
    which = which or shutil.which
    has_module = has_module or _has_module
    profile = profile or {}
    checks = []

    # 1) 听（语音转文字）——可选，缺了就退化成键盘输入
    stt = "faster-whisper" if has_module("faster_whisper") else (
        "openai-whisper" if has_module("whisper") else "")
    checks.append(("听·语音转文字", bool(stt),
                   f"用 {stt}" if stt else "未安装（可改用键盘输入）",
                   "pip install faster-whisper"))

    # 2) 麦克风录音——可选
    mic = has_module("sounddevice") and has_module("numpy")
    checks.append(("听·麦克风录音", mic,
                   "sounddevice 就绪" if mic else "缺 sounddevice/numpy（无法录音）",
                   "pip install sounddevice numpy"))

    # 3) 说（合成嗓音）——至少要有一样，否则只能打印
    pyttsx = has_module("pyttsx3")
    sys_say = bool(which("say"))
    sys_espeak = bool(which("espeak-ng") or which("espeak"))
    say_ok = pyttsx or sys_say or sys_espeak
    if sys_say:
        how = "用系统自带 say（Mac，中文质量好）"
    elif pyttsx:
        how = "用 pyttsx3"
    elif sys_espeak:
        how = "用系统自带 espeak"
    else:
        how = "没有任何 TTS 引擎，只能打印文字"
    checks.append(("说·合成嗓音", say_ok, how,
                   "Mac 自带 say；Linux: apt install espeak-ng；或 pip install pyttsx3"))

    # 4) 放音（克隆嗓音要把 wav 放出来）
    player = next((p for p in _PLAYERS if which(p)), "")
    checks.append(("放·音频播放器", bool(player),
                   f"用 {player}" if player else "没有播放器（克隆嗓音放不出声）",
                   "Mac 自带 afplay；Linux: apt install alsa-utils（aplay）或 ffmpeg（ffplay）"))

    # 5) 克隆嗓音命令（接了才查）
    cmd = profile.get("tts_cmd") if isinstance(profile, dict) else None
    if cmd:
        prog = str(cmd).strip().split()[0] if str(cmd).strip() else ""
        prog_ok = bool(which(prog)) if prog else False
        checks.append(("克隆·voice.tts_cmd", prog_ok,
                       f"命令 `{prog}` " + ("找得到 ✓" if prog_ok else "找不到，先确认装了/起了服务"),
                       "见 docs/voice_clone.md：GPT-SoVITS / CosyVoice2"))
    else:
        checks.append(("克隆·voice.tts_cmd", None,
                       "没配——现在用系统嗓音；想要本人声线就配上 tts_cmd",
                       "在 config/identity.yaml 的 voice.tts_cmd 填克隆命令（含 {text}）"))
    return checks


def format_diagnostics(checks) -> str:
    """把体检结果排成给人看的清单。"""
    lines = ["🎧 语音链路体检："]
    for name, ok, detail, fix in checks:
        mark = "✅" if ok else ("⚠️ " if ok is None else "❌")
        lines.append(f"  {mark} {name}：{detail}")
        if ok is False:
            lines.append(f"       └ 补：{fix}")
    # 结论
    can_speak = any(n == "说·合成嗓音" and ok for n, ok, *_ in checks)
    lines.append("结论：" + ("能出声了 👍" if can_speak else "还出不了声，先把「说·合成嗓音」补上"))
    return "\n".join(lines)
