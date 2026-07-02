"""神话传说测试。可直接运行：python tests/test_myths.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.myths import about, find_myth, is_myth_query, myths  # noqa: E402


def test_myths_cover():
    ms = myths()
    for m in ("盘古开天", "女娲补天", "后羿射日", "嫦娥奔月"):
        assert m in ms


def test_about():
    assert "劈开" in about("盘古开天") or "斧" in about("盘古开天")
    assert "五彩石" in about("女娲补天")
    assert about("奥特曼") == ""


def test_find_alias_longest():
    assert find_myth("盘古的故事") == "盘古开天"        # 别名
    assert find_myth("精卫填海是什么意思") == "精卫填海"
    assert find_myth("讲讲女娲") == "女娲补天"
    assert find_myth("今天天气") == ""


def test_about_from_sentence():
    assert "月亮" in about("嫦娥奔月的故事") or "广寒宫" in about("嫦娥奔月的故事")


def test_is_myth_query():
    assert is_myth_query("盘古开天的故事")
    assert is_myth_query("讲个神话传说")
    assert is_myth_query("夸父逐日是什么")
    assert not is_myth_query("今天几号")
    assert not is_myth_query("我叫盘古")               # 没问故事


def test_config_add():
    cfg = {"myths": {"沉香救母": "沉香劈山救出被压华山的母亲。"}}
    assert "沉香救母" in myths(cfg)
    assert "华山" in about("沉香救母的故事", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ myths: all tests passed")
