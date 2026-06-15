"""设备 / 家居控制（贾维斯："把灯关了"）。

默认用内存模拟后端（灯/空调/音乐/门/窗帘/电视），状态可读可控；
换上实现了同样 apply() 接口的后端（如 Home Assistant）即可对接真实家居。
自然语言解析为纯函数，零依赖、可单测。
"""

from __future__ import annotations

import re

_DEVICES = {
    "灯": "light", "电灯": "light", "灯光": "light",
    "空调": "ac", "冷气": "ac", "暖气": "ac",
    "音乐": "music", "歌": "music", "音响": "music",
    "门锁": "door", "门": "door",
    "窗帘": "curtain",
    "电视": "tv", "电视机": "tv",
}
_LABEL = {"light": "灯", "ac": "空调", "music": "音乐", "door": "门", "curtain": "窗帘", "tv": "电视"}

_OFF = ("关", "关闭", "停", "停止", "锁", "闭")
_ON = ("开", "打开", "启动", "来点", "来首", "放", "播放", "解锁", "拉开")
_SET = ("调到", "设为", "调成", "设成", "调至", "调高到", "调低到")


def parse_device_command(text: str):
    """把一句话解析成 (device, action, value)。不是设备指令则返回 None。

    例：'把灯关了'→('light','off',None)；'空调调到26度'→('ac','set',26)；'放点音乐'→('music','on',None)
    """
    text = text or ""
    device = next((v for k, v in _DEVICES.items() if k in text), None)
    if not device:
        return None
    m = re.search(r"(\d+)", text)
    value = int(m.group(1)) if m else None
    if any(w in text for w in _SET) and value is not None:
        return (device, "set", value)
    if any(w in text for w in _OFF):
        return (device, "off", None)
    if any(w in text for w in _ON):
        return (device, "on", None)
    if value is not None:                 # "空调26度"
        return (device, "set", value)
    return None


class SimDeviceBackend:
    """内存模拟：记录每个设备的开关与档位。"""

    def __init__(self, devices=None) -> None:
        names = devices or ["light", "ac", "music", "door", "curtain"]
        self.state = {n: {"power": "off"} for n in names}
        if "ac" in self.state:
            self.state["ac"]["temp"] = 26

    def names(self):
        return list(self.state)

    def states(self):
        return {k: dict(v) for k, v in self.state.items()}

    def apply(self, device, action, value=None) -> dict:
        if device not in self.state:
            return {"ok": False, "msg": f"没有找到设备：{device}"}
        st = self.state[device]
        label = _LABEL.get(device, device)
        if action == "off":
            st["power"] = "off"
            msg = "已锁门" if device == "door" else f"已关闭{label}"
        elif action == "on":
            st["power"] = "on"
            msg = "已开门" if device == "door" else f"已开启{label}"
        elif action == "set":
            st["power"] = "on"
            if device == "ac":
                st["temp"] = value
                msg = f"空调已设为 {value} 度"
            elif device == "music":
                st["volume"] = value
                msg = f"音量已设为 {value}"
            else:
                st["level"] = value
                msg = f"{label}已设为 {value}"
        else:
            return {"ok": False, "msg": "不支持的操作"}
        return {"ok": True, "device": device, "state": dict(st), "msg": msg}


class DeviceHub:
    def __init__(self, devices=None, backend=None) -> None:
        self.backend = backend or SimDeviceBackend(devices)

    def names(self):
        return self.backend.names()

    def states(self):
        return self.backend.states()

    def control(self, device, action, value=None) -> dict:
        return self.backend.apply(device, action, value)

    def describe(self) -> list[str]:
        """人类可读的设备状态，供网页展示。"""
        out = []
        for n, st in self.states().items():
            label = _LABEL.get(n, n)
            on = st.get("power") == "on"
            extra = ""
            if on and n == "ac" and "temp" in st:
                extra = f" {st['temp']}度"
            elif on and n == "music" and "volume" in st:
                extra = f" 音量{st['volume']}"
            elif on and "level" in st:
                extra = f" {st['level']}"
            out.append(f"{label}：{'开' if on else '关'}{extra}")
        return out

    def rows(self) -> list[dict]:
        """结构化设备状态，供网页渲染开关按钮。"""
        out = []
        for n, st in self.states().items():
            on = st.get("power") == "on"
            detail = ""
            if on and n == "ac" and "temp" in st:
                detail = f"{st['temp']}度"
            elif on and n == "music" and "volume" in st:
                detail = f"音量{st['volume']}"
            elif on and "level" in st:
                detail = str(st["level"])
            out.append({"key": n, "label": _LABEL.get(n, n), "on": on, "detail": detail})
        return out
