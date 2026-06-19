"""成语词典测试。可直接运行：python tests/test_idioms_dict.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.idioms_dict import (  # noqa: E402
    explain,
    find,
    idioms,
    is_idiom_lookup,
)


def test_idioms_count():
    assert len(idioms()) >= 40
    assert "雪中送炭" in idioms() and "相濡以沫" in idioms()


def test_explain():
    assert "及时的帮助" in explain("雪中送炭")
    assert "多余" in explain("画蛇添足")
    assert explain("查无此成语") == ""


def test_explain_from_sentence():
    s = explain("相濡以沫是什么意思")
    assert "扶持" in s or "不离不弃" in s


def test_find_in_text():
    assert find("守株待兔什么意思") == "守株待兔"
    assert find("今天天气好") == ""


def test_is_idiom_lookup():
    assert is_idiom_lookup("雪中送炭什么意思")
    assert is_idiom_lookup("解释一下卧薪尝胆")
    assert is_idiom_lookup("精益求精怎么用")
    assert not is_idiom_lookup("今天几号")
    assert not is_idiom_lookup("我们要白头偕老")          # 没问意思


def test_config_add():
    cfg = {"idioms": {"自强不息": ["努力向上、永不松懈。", "褒义。"]}}
    assert "自强不息" in idioms(cfg)
    assert "永不松懈" in explain("自强不息", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ idioms_dict: all tests passed")
