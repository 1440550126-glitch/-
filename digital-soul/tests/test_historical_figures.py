"""历史名人测试。可直接运行：python tests/test_historical_figures.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.historical_figures import (  # noqa: E402
    about,
    figures,
    find_figure,
    is_figure_query,
)


def test_figures_cover():
    fs = figures()
    for f in ("孔子", "李白", "诸葛亮", "岳飞"):
        assert f in fs


def test_about():
    assert "儒家" in about("孔子")
    assert "诗仙" in about("李白")
    assert about("钢铁侠") == ""


def test_find_alias_longest():
    assert find_figure("孔明是谁") == "诸葛亮"          # 别名
    assert find_figure("诗圣是谁") == "杜甫"
    assert find_figure("今天天气") == ""


def test_about_from_sentence():
    assert "抗金" in about("岳飞是什么人")


def test_is_figure_query():
    assert is_figure_query("孔子是谁")
    assert is_figure_query("李白哪个朝代的")
    assert is_figure_query("诸葛亮做了什么")
    assert not is_figure_query("今天几号")
    assert not is_figure_query("我儿子叫李白")          # 没问是谁/简介


def test_config_add():
    cfg = {"figures": {"扁鹊": ["战国", "神医，望闻问切。"]}}
    assert "扁鹊" in figures(cfg)
    assert "神医" in about("扁鹊是谁", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ historical_figures: all tests passed")
