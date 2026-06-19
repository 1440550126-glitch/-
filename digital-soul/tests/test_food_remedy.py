"""食疗测试。可直接运行：python tests/test_food_remedy.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.food_remedy import advice, detect, is_remedy_query  # noqa: E402


def test_detect():
    assert detect("最近老咳嗽") == "咳嗽"
    assert detect("有点上火") == "上火"
    assert detect("总睡不好") == "睡不好"
    assert detect("今天天气好") is None


def test_is_remedy_query():
    assert is_remedy_query("咳嗽吃什么好")
    assert is_remedy_query("上火喝什么")
    assert is_remedy_query("睡不好怎么调理")
    assert not is_remedy_query("咳嗽")                # 没问吃啥
    assert not is_remedy_query("吃什么好")            # 没具体症状


def test_advice():
    assert "冰糖雪梨" in advice("咳嗽吃什么好")
    assert "绿豆汤" in advice("上火喝什么")
    assert "小米粥" in advice("睡不好吃点什么") or "牛奶" in advice("睡不好吃点什么")
    assert advice("聊聊天") == ""


def test_advice_not_replacing_doctor():
    # 咳嗽久了提示就医
    assert "看看" in advice("咳嗽吃什么") or "医生" in advice("咳嗽吃什么")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ food_remedy: all tests passed")
