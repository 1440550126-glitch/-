"""动物小知识测试。可直接运行：python tests/test_animal_facts.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.animal_facts import (  # noqa: E402
    animals,
    fact_of,
    find_animal,
    is_animal_fact_query,
)


def test_animals_cover():
    a = animals()
    for x in ("熊猫", "老虎", "企鹅", "蜜蜂"):
        assert x in a


def test_fact_of():
    assert "竹子" in fact_of("熊猫")
    assert "夜里" in fact_of("猫头鹰") or "老鼠" in fact_of("猫头鹰")
    assert fact_of("机器猫") == ""


def test_find_alias_longest():
    assert find_animal("大熊猫吃什么") == "熊猫"        # 别名
    assert find_animal("小燕子是什么动物") == "燕子"
    assert find_animal("今天天气") == ""


def test_fact_from_sentence():
    assert "竹子" in fact_of("熊猫吃什么")


def test_is_animal_fact_query():
    assert is_animal_fact_query("熊猫吃什么")
    assert is_animal_fact_query("猫头鹰有什么本领")
    assert is_animal_fact_query("企鹅住在哪")
    assert not is_animal_fact_query("今天几号")
    assert not is_animal_fact_query("我家养了只猫")       # 没问习性（且‘猫’不在表）


def test_config_add():
    cfg = {"animal_facts": {"考拉": "住澳洲，爱吃桉树叶，一天睡20小时。"}}
    assert "考拉" in animals(cfg)
    assert "桉树叶" in fact_of("考拉吃什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ animal_facts: all tests passed")
