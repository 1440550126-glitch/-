"""场景 / 例程测试。可直接运行：python tests/test_scenes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.authority import Authority  # noqa: E402
from dsoul.devices import DeviceHub  # noqa: E402
from dsoul.scenes import SceneBook, parse_scene  # noqa: E402


def test_parse_scene_name_and_alias():
    names = ["回家模式", "睡眠模式", "离家模式"]
    assert parse_scene("启动回家模式", names) == "回家模式"
    assert parse_scene("我回来了", names) == "回家模式"     # 别名
    assert parse_scene("晚安", names) == "睡眠模式"
    assert parse_scene("今天天气不错", names) is None


def test_scenebook_run_applies_devices():
    sb = SceneBook()
    dh = DeviceHub()
    msgs = sb.run("回家模式", dh)
    assert msgs and dh.states()["light"]["power"] == "on"
    assert dh.states()["ac"]["temp"] == 26
    sb.run("离家模式", dh)
    assert dh.states()["light"]["power"] == "off" and dh.states()["door"]["power"] == "off"


def test_config_overrides_defaults():
    sb = SceneBook({"scenes": {"专注模式": [["light", "on"], ["music", "off"]]}})
    assert "专注模式" in sb.names() and "回家模式" in sb.names()  # 覆盖叠加在默认之上


def _agent():
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
    a.scenes = SceneBook()
    return a


def test_run_scene_authorization():
    a = _agent()
    assert a.run_scene("张明", "回家模式")["ok"] is True
    assert a.run_scene("路人", "回家模式")["ok"] is False         # 陌生人不能动家居
    assert a._scene_route("张明", "我回来了").startswith("已启动")
    assert a._scene_route("张明", "随便聊聊") is None


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ scenes: all tests passed")
