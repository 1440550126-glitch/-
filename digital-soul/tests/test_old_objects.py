"""怀旧老物件测试。可直接运行：python tests/test_old_objects.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.old_objects import (  # noqa: E402
    count, find_object, is_old_object_query, memory_of, objects, recall,
)


def test_objects_present():
    os_ = objects()
    for k in ("搪瓷缸", "煤油灯", "缝纫机", "粮票", "二八大杠"):
        assert k in os_
    assert count() >= 12


def test_find_object_alias_longest():
    assert find_object("那个搪瓷缸子")[0] == "搪瓷缸"
    assert find_object("骑二八自行车")[0] == "二八大杠"      # 别名
    assert find_object("听半导体")[0] == "收音机"
    assert find_object("今天天气好") is None


def test_memory_text():
    m = memory_of("还记得粮票吗")
    assert "票" in m and len(m) > 8
    assert memory_of("随便聊聊") == ""


def test_recall_opens_topic():
    s = recall(seed="x")
    assert "还记得" in s and "老物件" in s


def test_recall_deterministic():
    assert recall(seed="same") == recall(seed="same")


def test_is_query_gating():
    assert is_old_object_query("还记得粮票吗")
    assert is_old_object_query("聊聊老物件")
    assert is_old_object_query("以前用过煤油灯")
    assert not is_old_object_query("今天天气好")
    assert not is_old_object_query("缝纫机")               # 光提名字、没有怀旧意图 → 不抢


def test_config_extra_object():
    cfg = {"old_objects": {"items": [["铁皮青蛙", ["发条青蛙"], "铁皮玩具", "上了发条会蹦的铁皮青蛙，男孩子的宝贝"]]}}
    assert "铁皮青蛙" in objects(cfg)
    assert find_object("发条青蛙", cfg)[0] == "铁皮青蛙"
    assert "发条" in memory_of("还记得铁皮青蛙吗", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ old_objects: all tests passed")
