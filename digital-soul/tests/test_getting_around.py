"""出行帮手测试。可直接运行：python tests/test_getting_around.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.getting_around import (  # noqa: E402
    ask_directions_script, count, find_mode, how_to,
    is_getting_around_query, modes, safety_tips,
)


def test_modes_present():
    ms = modes()
    for k in ("公交车", "地铁", "网约车", "高铁火车", "飞机", "步行问路"):
        assert k in ms
    assert count() >= 6


def test_find_mode_alias():
    assert find_mode("地铁怎么坐") == "地铁"
    assert find_mode("滴滴怎么叫车") == "网约车"
    assert find_mode("打的去") == "出租车"
    assert find_mode("坐火车回家") == "高铁火车"
    assert find_mode("今天天气好") is None


def test_how_to_has_steps_and_tip():
    s = how_to("地铁")
    assert "安检" in s and "换乘" in s and "提醒" in s
    assert how_to("网约车").find("核对车牌") != -1            # 安全要点在
    assert how_to("不存在") == ""


def test_how_to_via_alias():
    assert how_to("滴滴").startswith("网约车怎么坐")           # 别名也能查


def test_ask_directions_and_tips():
    assert "请问" in ask_directions_script()
    t = safety_tips()
    assert len(t) >= 4
    assert any("身份证" in x for x in t) and any("紧急联系人" in x or "家人" in x for x in t)


def test_is_query_gating():
    assert is_getting_around_query("地铁怎么坐")
    assert is_getting_around_query("打车软件怎么用")
    assert is_getting_around_query("出门怕走丢咋办")
    assert not is_getting_around_query("今天天气好")
    assert not is_getting_around_query("我要坐地铁去医院")     # 陈述出行意图，不是问怎么坐


def test_config_extra_mode():
    cfg = {"getting_around": {"modes": {"轮渡": ["①码头买票上船；②扶好栏杆别靠太外", "风大穿厚点"]}}}
    assert "轮渡" in modes(cfg)
    assert how_to("轮渡", cfg).startswith("轮渡怎么坐")
    assert find_mode("轮渡怎么坐", cfg) == "轮渡"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ getting_around: all tests passed")
