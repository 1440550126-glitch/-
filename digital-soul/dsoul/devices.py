"""设备 / 家居控制（贾维斯："把灯关了"）。

默认用内存模拟后端（灯/空调/音乐/门/窗帘/电视），状态可读可控；
换上实现了同样 apply() 接口的后端（如 Home Assistant）即可对接真实家居。
自然语言解析为纯函数，零依赖、可单测。
"""

from __future__ import annotations

import json
import re
import urllib.request

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


# 把 HA 实体状态归一成"开/关"
_ON_STATES = {"on", "open", "unlocked", "playing", "home", "heat", "cool", "auto"}


class HomeAssistantBackend:
    """对接真实家居：把设备指令翻译成 Home Assistant 的 REST 服务调用。

    需要 base_url（如 http://homeassistant.local:8123）、长期令牌 token，
    以及逻辑设备→实体的映射 entities（如 {"light":"light.living_room"}）。
    与 SimDeviceBackend 接口一致，可直接替换。
    """

    def __init__(self, base_url, token, entities=None) -> None:
        self.base = base_url.rstrip("/")
        self.token = token
        self.entities = entities or {}

    def names(self):
        return list(self.entities)

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

    def _svc(self, domain, service, entity, extra=None):
        body = {"entity_id": entity}
        if extra:
            body.update(extra)
        return self._request("POST", f"/api/services/{domain}/{service}", body)

    def apply(self, device, action, value=None) -> dict:
        entity = self.entities.get(device)
        if not entity:
            return {"ok": False, "msg": f"未映射设备：{device}"}
        domain = entity.split(".")[0]
        label = _LABEL.get(device, device)
        try:
            if action == "off":
                self._svc("lock", "lock", entity) if domain == "lock" else self._svc(domain, "turn_off", entity)
                msg = "已锁门" if device == "door" else f"已关闭{label}"
            elif action == "on":
                if domain == "lock":
                    self._svc("lock", "unlock", entity)
                elif domain == "media_player":
                    self._svc("media_player", "media_play", entity)
                else:
                    self._svc(domain, "turn_on", entity)
                msg = "已开门" if device == "door" else f"已开启{label}"
            elif action == "set":
                if domain == "climate":
                    self._svc("climate", "set_temperature", entity, {"temperature": value})
                    msg = f"空调已设为 {value} 度"
                elif domain == "media_player":
                    self._svc("media_player", "volume_set", entity, {"volume_level": min(1.0, (value or 0) / 100)})
                    msg = f"音量已设为 {value}"
                else:
                    self._svc(domain, "turn_on", entity)
                    msg = f"{label}已设为 {value}"
            else:
                return {"ok": False, "msg": "不支持的操作"}
        except Exception as e:  # 网络/认证失败兜底，不让分身崩
            return {"ok": False, "msg": f"调用 Home Assistant 失败：{e}"}
        return {"ok": True, "device": device, "msg": msg}

    def states(self):
        out = {}
        for n, entity in self.entities.items():
            try:
                raw = self._request("GET", f"/api/states/{entity}").get("state", "")
            except Exception:
                raw = "unknown"
            out[n] = {"power": "on" if raw in _ON_STATES else "off", "raw": raw}
        return out


def build_device_hub(config=None) -> DeviceHub:
    """按配置选后端：配了 home_assistant 就接真机，否则用内存模拟。"""
    ha = config.get("home_assistant") if isinstance(config, dict) else None
    if ha and ha.get("base_url") and ha.get("token"):
        return DeviceHub(backend=HomeAssistantBackend(ha["base_url"], ha["token"], ha.get("entities", {})))
    return DeviceHub()


class HASensors:
    """从 Home Assistant 读取传感器数值（供温度等条件触发用）。"""

    def __init__(self, base_url, token, entities) -> None:
        self.base = base_url.rstrip("/")
        self.token = token
        self.entities = entities or {}

    def _get(self, entity):
        req = urllib.request.Request(
            self.base + f"/api/states/{entity}",
            headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def read(self) -> dict:
        out = {}
        for name, entity in self.entities.items():
            try:
                out[name] = float(self._get(entity).get("state"))
            except Exception:
                pass
        return out


def build_sensor_source(config=None):
    """配了 home_assistant.sensors 就读真实传感器，否则返回 None（用模拟读数）。"""
    ha = config.get("home_assistant") if isinstance(config, dict) else None
    if ha and ha.get("base_url") and ha.get("token") and ha.get("sensors"):
        return HASensors(ha["base_url"], ha["token"], ha["sensors"])
    return None
