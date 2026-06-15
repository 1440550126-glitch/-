"""多步任务编排测试。可直接运行：python tests/test_orchestrate.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.authority import Authority  # noqa: E402
from dsoul.devices import DeviceHub  # noqa: E402
from dsoul.orchestrator import orchestrate, split_steps  # noqa: E402


def test_split_steps():
    assert split_steps("把灯关了，再放点音乐") == ["把灯关了", "放点音乐"]
    assert split_steps("订明天的会议并通知大家") == ["订明天的会议", "通知大家"]


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
    a.hub = None                       # 不接外部智能体，纯设备多步（离线可测）
    return a


def test_orchestrate_multi_device():
    a = _agent()
    out = orchestrate(a, "张明", "把灯打开，再放点音乐", addr="先生")
    assert out is not None
    assert "已开启灯" in out and "已开启音乐" in out
    assert a.devices.states()["light"]["power"] == "on"


def test_single_step_returns_none():
    a = _agent()
    assert orchestrate(a, "张明", "把灯打开", addr="先生") is None   # 单步交回普通流程


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ orchestrate: all tests passed")
