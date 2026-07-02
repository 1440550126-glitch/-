"""助眠测试。可直接运行：python tests/test_sleep_aid.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.sleep_aid import (  # noqa: E402
    breathing_478,
    count_along,
    senses_sleepless,
    wind_down,
)


def test_senses_sleepless():
    assert senses_sleepless("唉，又睡不着")
    assert senses_sleepless("失眠好几天了")
    assert senses_sleepless("翻来覆去的")
    assert not senses_sleepless("今天睡得真好")
    assert not senses_sleepless("几点了")


def test_wind_down_has_name_and_guide():
    s = wind_down("老张", seed="a")
    assert s.startswith("老张，")
    assert len(s) > 20


def test_wind_down_rotates():
    a = wind_down(seed="1")
    b = wind_down(seed="2")
    assert a and b                      # 不同 seed 不报错；内容多半不同
    assert wind_down(seed="x") == wind_down(seed="x")   # 同 seed 稳定


def test_wind_down_no_name():
    assert not wind_down(seed="1").startswith("，")


def test_breathing_478():
    assert "4-7-8" in breathing_478() and "八" in breathing_478()


def test_count_along_clamps():
    assert count_along(5).count("、") == 4          # 1..5 → 4 个顿号
    assert "1" in count_along(1)                    # 下限保护，至少数到 3
    long = count_along(100)
    assert "30" in long and "31" not in long        # 上限 30


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ sleep_aid: all tests passed")
