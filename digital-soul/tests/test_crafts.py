"""传统手工艺测试。可直接运行：python tests/test_crafts.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.crafts import about, crafts, find_craft, is_craft_query  # noqa: E402


def test_crafts_cover():
    cs = crafts()
    for c in ("剪纸", "刺绣", "陶瓷", "景泰蓝"):
        assert c in cs


def test_about():
    assert "窗花" in about("剪纸") or "红纸" in about("剪纸")
    assert "景德镇" in about("陶瓷")
    assert about("3D打印") == ""


def test_find_alias_longest():
    assert find_craft("苏绣是什么") == "刺绣"          # 别名
    assert find_craft("青花瓷怎么做") == "陶瓷"
    assert find_craft("今天天气") == ""


def test_about_from_sentence():
    assert "潍坊" in about("风筝是哪里的")


def test_is_craft_query():
    assert is_craft_query("剪纸怎么做")
    assert is_craft_query("传统手工艺有哪些")
    assert is_craft_query("景泰蓝是什么")
    assert not is_craft_query("今天几号")
    assert not is_craft_query("我会剪纸")               # 没问介绍


def test_config_add():
    cfg = {"crafts": {"竹编": "篾匠用竹条编篮筐器物，南方常见。"}}
    assert "竹编" in crafts(cfg)
    assert "篾匠" in about("竹编是什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ crafts: all tests passed")
