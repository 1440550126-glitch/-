"""曲艺测试。可直接运行：python tests/test_quyi.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.quyi import (  # noqa: E402
    count, describe, find_form, forms, is_quyi_query, recall,
)


def test_forms_present():
    fs = forms()
    for k in ("相声", "评书", "快板", "京韵大鼓", "苏州评弹", "山东快书"):
        assert k in fs
    assert count() >= 8


def test_find_form_alias():
    assert find_form("评书就是说书吧")[0] == "评书"
    assert find_form("来段山东快书")[0] == "山东快书"
    assert find_form("对口相声")[0] == "相声"
    assert find_form("今天天气好") is None


def test_describe_has_intro_and_stars():
    s = describe("相声")
    assert "说学逗唱" in s and "代表" in s and ("侯宝林" in s or "马三立" in s)
    assert "醒木" in describe("评书")
    assert describe("不存在") == ""


def test_recall_opens_topic():
    s = recall(seed="y")
    assert "曲艺" in s


def test_is_quyi_query_gating():
    assert is_quyi_query("相声是什么")
    assert is_quyi_query("聊聊曲艺")
    assert is_quyi_query("想听段山东快书")
    assert not is_quyi_query("今天天气好")
    assert not is_quyi_query("京韵大鼓")                   # 光提名字、没意图 → 不抢


def test_distinct_from_opera():
    # 曲艺是说唱，不该混进京剧越剧这类戏曲剧种
    assert find_form("京剧怎么样") is None


def test_config_extra_form():
    cfg = {"quyi": {"forms": [["天津时调", ["时调"], "天津的鼓曲小调，俏皮上口", "王毓宝"]]}}
    assert "天津时调" in forms(cfg)
    assert find_form("听段时调", cfg)[0] == "天津时调"
    assert "王毓宝" in describe("天津时调", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ quyi: all tests passed")
