"""Home Assistant 后端测试（离线，打桩请求）。python tests/test_ha.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.devices import DeviceHub, HomeAssistantBackend, build_device_hub  # noqa: E402
from dsoul.devices import HASensors, build_sensor_source  # noqa: E402


class _Rec(HomeAssistantBackend):
    """记录请求、返回假数据，不走真实网络。"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.calls = []

    def _request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        return {"state": "on"} if method == "GET" else {}


def _backend():
    return _Rec("http://h:8123", "tok", {
        "light": "light.lr", "ac": "climate.bd", "door": "lock.fd", "music": "media_player.m",
    })


def test_apply_maps_to_ha_services():
    b = _backend()
    assert b.apply("light", "on") == {"ok": True, "device": "light", "msg": "已开启灯"}
    assert b.calls[-1] == ("POST", "/api/services/light/turn_on", {"entity_id": "light.lr"})
    b.apply("ac", "set", 24)
    assert b.calls[-1] == ("POST", "/api/services/climate/set_temperature",
                           {"entity_id": "climate.bd", "temperature": 24})
    b.apply("door", "off")                       # 锁门 → lock.lock
    assert b.calls[-1] == ("POST", "/api/services/lock/lock", {"entity_id": "lock.fd"})
    b.apply("music", "on")                       # 音乐 → media_play
    assert b.calls[-1] == ("POST", "/api/services/media_player/media_play", {"entity_id": "media_player.m"})


def test_states_normalized_to_power():
    b = _Rec("http://h:8123", "tok", {"light": "light.lr"})
    assert b.states()["light"]["power"] == "on"


def test_unmapped_device():
    b = _Rec("http://h:8123", "tok", {})
    assert b.apply("light", "on")["ok"] is False


def test_build_device_hub_selects_backend():
    assert isinstance(build_device_hub({}), DeviceHub)                 # 无配置 → 模拟
    assert build_device_hub({}).control("light", "on")["msg"] == "已开启灯"
    hub = build_device_hub({"home_assistant": {
        "base_url": "http://h:8123", "token": "t", "entities": {"light": "light.x"}}})
    assert isinstance(hub.backend, HomeAssistantBackend)               # 有配置 → 真机


def test_ha_sensors_read():
    class _S(HASensors):
        def _get(self, entity):
            return {"state": "16.5"}
    s = _S("http://h:8123", "tok", {"temperature": "sensor.t"})
    assert s.read() == {"temperature": 16.5}


def test_build_sensor_source():
    assert build_sensor_source({}) is None                            # 无传感器配置
    src = build_sensor_source({"home_assistant": {
        "base_url": "http://h:8123", "token": "t", "sensors": {"temperature": "sensor.t"}}})
    assert isinstance(src, HASensors)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ ha: all tests passed")
