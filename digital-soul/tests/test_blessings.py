"""祝福语测试。可直接运行：python tests/test_blessings.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.blessings import (  # noqa: E402
    bless_for,
    detect_occasion,
    is_blessing_request,
    normalize_occasion,
    occasions,
)


def test_occasions_cover():
    for o in ("生日", "结婚", "乔迁", "寿宴", "拜年"):
        assert o in occasions()


def test_normalize_alias():
    assert normalize_occasion("过年") == "拜年"
    assert normalize_occasion("大寿") == "寿宴"
    assert normalize_occasion("搬家") == "乔迁"
    assert normalize_occasion("出院") == "康复"
    assert normalize_occasion("不相关") == ""


def test_detect_occasion():
    assert detect_occasion("朋友结婚，说句祝福语") == "结婚"
    assert detect_occasion("老人家过大寿") == "寿宴"
    assert detect_occasion("给长辈拜年说点啥") == "拜年"
    assert detect_occasion("今天天气不错") == ""


def test_detect_prefers_specific():
    # "搬家"→乔迁，不被泛词干扰
    assert detect_occasion("同事搬家乔迁") == "乔迁"


def test_bless_for_rotates_and_matches():
    s = bless_for("结婚", seed="a")
    assert any(w in s for w in ("同心", "白头", "佳偶", "恩恩爱爱", "甜甜蜜蜜", "新婚", "好合"))
    # 别名也能取
    assert bless_for("过年", seed="x")
    assert bless_for("不是场合") == ""


def test_bless_for_birthday():
    assert "生日快乐" in bless_for("生日", seed="0")


def test_is_blessing_request():
    assert is_blessing_request("说句祝福语")
    assert is_blessing_request("拜年话怎么说")
    assert is_blessing_request("讨个口彩")
    assert not is_blessing_request("今天几号")


def test_config_add_and_override():
    cfg = {"blessings": {"生日": "自家话：生日快乐，长命百岁！", "谢师": ["谢谢老师栽培！"]}}
    assert "长命百岁" in bless_for("生日", seed="", config=cfg)   # 自家的排在前，空 seed 取首条
    assert "谢谢老师" in bless_for("谢师", config=cfg)
    assert detect_occasion("给老师的谢师宴", cfg) == "谢师"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ blessings: all tests passed")
