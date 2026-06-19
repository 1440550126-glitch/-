"""姓氏起源测试。可直接运行：python tests/test_surnames.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.surnames import (  # noqa: E402
    about,
    find_surname,
    is_surname_query,
    surnames,
)


def test_surnames_count():
    ss = surnames()
    assert len(ss) >= 25
    for s in ("李", "王", "张", "刘", "陈", "赵", "钱"):
        assert s in ss


def test_about():
    assert "李白" in about("李")
    assert "赵匡胤" in about("赵")
    assert about("某") == ""


def test_about_no_garble():
    # 确认没有残留笔误
    for s in surnames():
        a = about(s)
        assert "replace" not in a and "independence" not in a


def test_find_surname():
    assert find_surname("我姓李") == "李"
    assert find_surname("张姓的来历") == "张"
    assert find_surname("讲讲钱姓") == "钱"
    assert find_surname("今天天气") == ""


def test_about_from_sentence():
    assert "王羲之" in about("王姓的起源")


def test_is_surname_query():
    assert is_surname_query("我姓李，这个姓的来历")
    assert is_surname_query("张姓的起源")
    assert is_surname_query("讲讲我的姓，我姓刘")
    assert not is_surname_query("今天几号")
    assert not is_surname_query("李子真甜")            # 提到"李"但不是问姓氏


def test_config_add():
    cfg = {"surnames": {"龙": ["源出御龙氏；天水为望。", "龙太子、龙云"]}}
    assert "龙" in surnames(cfg)
    assert "龙云" in about("龙", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ surnames: all tests passed")
