"""家电帮手测试。可直接运行：python tests/test_appliances.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.appliances import (  # noqa: E402
    appliances, count, find_appliance, how_to, is_appliance_query,
)


def test_appliances_present():
    aps = appliances()
    for k in ("洗衣机", "微波炉", "电饭煲", "空调遥控器", "燃气灶"):
        assert k in aps
    assert count() >= 8


def test_find_appliance_alias():
    assert find_appliance("煤气灶打不着火") == "燃气灶"
    assert find_appliance("高压锅怎么用") == "电压力锅"
    assert find_appliance("电饭锅煮饭") == "电饭煲"
    assert find_appliance("今天天气好") is None


def test_how_to_has_steps_and_safety():
    s = how_to("微波炉")
    assert "门" in s and "安全" in s and "金属" in s          # 步骤 + 安全提醒
    assert how_to("不存在") == ""


def test_how_to_via_alias():
    assert how_to("煤气灶").startswith("燃气灶怎么用")
    assert "泄压" in how_to("高压锅")                         # 别名查电压力锅


def test_gas_safety_mentions_leak():
    s = how_to("燃气灶")
    assert "煤气味" in s and ("关阀" in s or "开窗" in s)     # 漏气先关阀开窗


def test_is_query_gating():
    assert is_appliance_query("洗衣机怎么用")
    assert is_appliance_query("空调遥控器怎么调")
    assert is_appliance_query("电视没画面咋办")
    assert not is_appliance_query("今天天气好")
    assert not is_appliance_query("洗衣机坏了")              # 报故障、没问怎么用 → 不抢


def test_config_extra_appliance():
    cfg = {"appliances": {"items": {"扫地机器人": ["放回充电座按开始就行", "先把地上电线收一收"]}}}
    assert "扫地机器人" in appliances(cfg)
    assert how_to("扫地机器人", cfg).startswith("扫地机器人怎么用")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ appliances: all tests passed")
