"""中国古代发明测试。可直接运行：python tests/test_inventions.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.inventions import (  # noqa: E402
    about,
    find_invention,
    four_inventions,
    inventions,
    is_invention_query,
)


def test_inventions_cover():
    its = inventions()
    for x in ("造纸术", "印刷术", "火药", "指南针", "算盘"):
        assert x in its


def test_four():
    f = four_inventions()
    assert "造纸术" in f and "指南针" in f


def test_about():
    assert "蔡伦" in about("造纸术")
    assert "张衡" in about("地动仪")
    assert about("互联网") == ""


def test_find_alias():
    assert find_invention("活字印刷是谁发明") == "印刷术"
    assert find_invention("司南是什么") == "指南针"
    assert find_invention("今天天气") == ""


def test_about_from_sentence():
    assert "李冰" in about("都江堰是谁修的") or "水利" in about("都江堰是谁修的")


def test_is_invention_query():
    assert is_invention_query("四大发明是什么")
    assert is_invention_query("造纸术谁发明的")
    assert is_invention_query("地动仪是什么")
    assert not is_invention_query("今天几号")


def test_config_add():
    cfg = {"inventions": {"火箭": "宋代就有火药做的‘火箭’，是现代火箭的雏形。"}}
    assert "火箭" in inventions(cfg)
    assert "火药" in about("火箭是什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ inventions: all tests passed")
