"""食物保存测试。可直接运行：python tests/test_food_storage.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.food_storage import (  # noqa: E402
    advice, count, find_topic, is_storage_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("冰箱分区", "剩菜保存", "别放冰箱", "解冻", "生熟分开"):
        assert k in ts
    assert count() >= 5


def test_find_topic_alias():
    assert find_topic("肉怎么化冻") == "解冻"
    assert find_topic("剩菜怎么存") == "剩菜保存"
    assert find_topic("剩饭能放多久") in ("能放多久", "剩菜保存")   # 都讲得通
    assert find_topic("案板要分开吗") == "生熟分开"
    assert find_topic("今天天气好") is None


def test_fridge_raw_cooked_separation():
    s = advice("冰箱分区")
    assert "生熟" in s and ("上层" in s or "下层" in s)


def test_leftovers_reheat():
    s = advice("剩菜保存")
    assert "热透" in s and ("2 天" in s or "绿叶菜" in s)


def test_what_not_to_fridge():
    s = advice("别放冰箱")
    assert "香蕉" in s and ("土豆" in s or "蜂蜜" in s)


def test_thaw_no_refreeze():
    s = advice("解冻")
    assert "别再冻" in s or "反复冻" in s


def test_is_query_gating():
    assert is_storage_query("冰箱怎么放")
    assert is_storage_query("剩菜能放多久")
    assert is_storage_query("肉怎么解冻")
    assert not is_storage_query("今天天气好")
    assert not is_storage_query("我买了个冰箱")           # 陈述、没问保存 → 不抢


def test_config_extra_topic():
    cfg = {"food_storage": {"topics": {"干货保存": ["密封防潮、阴凉避光", "生虫受潮就别吃"]}}}
    assert "干货保存" in topics(cfg)
    assert "防潮" in advice("干货保存", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ food_storage: all tests passed")
