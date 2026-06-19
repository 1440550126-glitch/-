"""灾害自救测试。可直接运行：python tests/test_disaster_safety.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.disaster_safety import (  # noqa: E402
    find_scenario,
    is_disaster_query,
    scenarios,
    tip_for,
)


def test_scenarios_cover():
    ss = scenarios()
    for s in ("地震", "台风", "洪水", "雷电"):
        assert s in ss


def test_tip_for():
    assert "承重墙" in tip_for("地震了怎么办") or "护住头" in tip_for("地震了怎么办")
    assert "湿毛巾" in tip_for("着火了怎么跑")
    assert "120" in tip_for("有人溺水怎么办")
    assert tip_for("外星人入侵") == ""


def test_find_scenario_longest():
    s = find_scenario("打雷了在外面怎么躲")
    assert s and s["name"] == "雷电"


def test_is_disaster_query():
    assert is_disaster_query("地震了怎么办")
    assert is_disaster_query("火灾逃生")
    assert is_disaster_query("打雷了怎么躲")
    assert not is_disaster_query("今天几号")
    assert not is_disaster_query("今天有点闷热")          # 没问自救


def test_config_add():
    cfg = {"disaster_safety": [{"name": "泥石流", "keys": ["泥石流"],
                                "tip": "往两侧高处跑，别顺沟方向逃。"}]}
    assert "泥石流" in scenarios(cfg)
    assert "高处" in tip_for("遇到泥石流怎么办", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ disaster_safety: all tests passed")
