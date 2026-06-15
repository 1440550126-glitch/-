"""设备 / 家居控制测试。可直接运行：python tests/test_devices.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.authority import Authority  # noqa: E402
from dsoul.devices import DeviceHub, parse_device_command  # noqa: E402


def test_parse_device_commands():
    assert parse_device_command("把灯关了") == ("light", "off", None)
    assert parse_device_command("开空调") == ("ac", "on", None)
    assert parse_device_command("空调调到26度") == ("ac", "set", 26)
    assert parse_device_command("放点音乐") == ("music", "on", None)
    assert parse_device_command("锁门") == ("door", "off", None)
    assert parse_device_command("灯好亮啊") is None        # 只是感叹，不是指令
    assert parse_device_command("今天天气不错") is None


def test_hub_control_and_describe():
    h = DeviceHub()
    assert h.control("light", "on")["msg"] == "已开启灯"
    assert h.control("ac", "set", 24)["state"]["temp"] == 24
    assert h.control("door", "off")["msg"] == "已锁门"
    desc = h.describe()
    assert any("灯：开" in d for d in desc)
    assert any("空调：开 24度" in d for d in desc)


def _agent_with_devices():
    rel = {
        "permissions": {"owner": ["*"], "stranger": []},
        "people": [
            {"name": "张明", "relation": "本人", "trust": "owner"},
            {"name": "路人", "relation": "陌生人", "trust": "stranger"},
        ],
    }
    a = object.__new__(Agent)
    a.authority = Authority(rel)
    a.devices = DeviceHub()
    return a


def test_owner_controls_stranger_denied():
    a = _agent_with_devices()
    assert a._device_route("张明", "把灯打开") == "已开启灯"
    denied = a._device_route("路人", "把灯关了")
    assert denied is not None and "已" not in denied        # 陌生人被拒，不执行
    assert a._device_route("张明", "你好呀") is None          # 非设备指令


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ devices: all tests passed")
