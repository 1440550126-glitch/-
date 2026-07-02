"""戏曲行当与脸谱测试。可直接运行：python tests/test_opera_roles.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.opera_roles import (  # noqa: E402
    count, explain, find_item, is_opera_role_query, items, roles_overview,
)


def test_items_present():
    its = items()
    for k in ("生", "旦", "净", "丑", "红脸", "黑脸", "白脸"):
        assert k in its
    assert count() >= 9


def test_find_item_alias():
    assert find_item("花旦是什么") == "旦"
    assert find_item("曹操脸是啥") == "白脸"
    assert find_item("武生演谁") == "生"
    assert find_item("今天天气好") is None


def test_face_color_meanings():
    assert "忠" in explain("红脸") and "关羽" in explain("红脸")
    assert "奸" in explain("白脸")
    assert "包公" in explain("黑脸") or "刚" in explain("黑脸")
    assert explain("不存在") == ""


def test_four_skills():
    s = explain("四功五法")
    assert "唱" in s and "念" in s and "做" in s and "打" in s


def test_overview():
    o = roles_overview()
    assert "生" in o and "旦" in o and "净" in o and "丑" in o


def test_is_query_gating():
    assert is_opera_role_query("生旦净丑是什么")
    assert is_opera_role_query("红脸代表什么")
    assert is_opera_role_query("唱念做打指什么")
    assert not is_opera_role_query("今天天气好")
    assert not is_opera_role_query("来段京剧")           # 起唱段 → 归 opera，不抢


def test_config_extra_item():
    cfg = {"opera_roles": {"items": {"髯口": "老生挂的假胡子，长短颜色显年龄身份"}}}
    assert "髯口" in items(cfg)
    assert "胡子" in explain("髯口", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ opera_roles: all tests passed")
