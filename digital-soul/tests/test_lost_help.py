"""迷路求助测试。可直接运行：python tests/test_lost_help.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.lost_help import guide, senses_lost  # noqa: E402


def test_senses_lost():
    assert senses_lost("我找不到家了")
    assert senses_lost("不知道自己在哪")
    assert senses_lost("好像迷路了")
    assert senses_lost("找不到回家的路")


def test_not_lost_for_objects():
    # 找不到东西归"找东西"，不是迷路
    assert not senses_lost("我找不到钥匙了")
    assert not senses_lost("老花镜找不着了")
    assert not senses_lost("今天天气怎么样")


def test_guide_generic():
    g = guide("张大爷")
    assert "张大爷" in g
    assert "站在原地" in g
    assert "穿制服" in g or "警察" in g
    assert "家里人" in g            # 没号码 → 通用打电话指引


def test_guide_with_contact_number():
    g = guide("张大爷", contact={"name": "儿子小明", "relation": "儿子", "phone": "13800001111"})
    assert "13800001111" in g
    assert "儿子" in g


def test_guide_contact_without_phone_falls_back():
    g = guide("", contact={"name": "小明"})       # 没 phone → 通用指引
    assert "家里人" in g


def test_guide_no_name_ok():
    g = guide()
    assert "别急" in g and "深吸一口气" in g


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ lost_help: all tests passed")
