"""书法字体测试。可直接运行：python tests/test_calligraphy.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.calligraphy import (  # noqa: E402
    about,
    find_script,
    four_masters,
    is_calligraphy_query,
    scripts,
)


def test_scripts_cover():
    ss = scripts()
    for s in ("楷书", "行书", "草书", "隶书", "篆书"):
        assert s in ss


def test_about():
    assert "端正" in about("楷书") or "初学" in about("楷书")
    assert "兰亭序" in about("行书")
    assert about("火星文") == ""


def test_about_facts():
    assert "王羲之" in about("兰亭序")
    assert "王羲之" in about("书圣是谁")


def test_find_alias_longest():
    assert find_script("正楷怎么写") == "楷书"          # 别名
    assert find_script("狂草是什么") == "草书"
    assert find_script("今天天气") == ""


def test_four_masters():
    fm = four_masters()
    assert "欧阳询" in fm and "颜真卿" in fm


def test_is_calligraphy_query():
    assert is_calligraphy_query("楷书是什么样")
    assert is_calligraphy_query("楷书四大家是谁")
    assert is_calligraphy_query("我想练毛笔字")
    assert not is_calligraphy_query("今天几号")


def test_config_add():
    cfg = {"calligraphy": {"瘦金体": "宋徽宗独创，瘦硬挺拔。"}}
    assert "瘦金体" in scripts(cfg)
    assert "宋徽宗" in about("瘦金体是什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ calligraphy: all tests passed")
