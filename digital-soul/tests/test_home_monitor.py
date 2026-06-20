"""居家监测测试。可直接运行：python tests/test_home_monitor.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.home_monitor import (  # noqa: E402
    count, find_item, how_to, is_monitor_query, items,
)


def test_items_present():
    its = items()
    for k in ("量血压", "测血糖", "量体温", "数脉搏", "称体重"):
        assert k in its
    assert count() >= 5


def test_find_item_alias():
    assert find_item("量心率怎么数") == "数脉搏"
    assert find_item("血糖怎么测") == "测血糖"
    assert find_item("体温量哪儿") == "量体温"
    assert find_item("今天天气好") is None


def test_how_to_has_steps_normal_disclaimer():
    s = how_to("量血压")
    assert "静坐" in s and "心脏一个高度" in s
    assert "120/80" in s                              # 正常参考
    assert "不替代看病" in s                          # 免责
    assert how_to("不存在") == ""


def test_blood_sugar_timing():
    s = how_to("测血糖")
    assert "空腹" in s and "餐后" in s and "第二滴" in s


def test_is_query_gating():
    assert is_monitor_query("血压怎么量才准")
    assert is_monitor_query("测血糖什么时候测")
    assert is_monitor_query("怎么数脉搏")
    assert not is_monitor_query("今天天气好")
    assert not is_monitor_query("我血压有点高")        # 陈述症状、不是问怎么量 → 留给体检/导诊


def test_config_extra_item():
    cfg = {"home_monitor": {"items": {"量血氧": {"how": "夹手指等读数稳定", "normal": "95%以上",
                                                "tip": "凉手测不准、搓热再夹"}}}}
    assert "量血氧" in items(cfg)
    assert "95%" in how_to("量血氧", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ home_monitor: all tests passed")
