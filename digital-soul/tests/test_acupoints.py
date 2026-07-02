"""穴位按摩测试。可直接运行：python tests/test_acupoints.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.acupoints import (  # noqa: E402
    count, describe, find_point, for_symptom, is_acupoint_query, points,
)


def test_points_present():
    ps = points()
    for k in ("合谷", "太阳穴", "足三里", "内关", "涌泉"):
        assert k in ps
    assert count() >= 10


def test_find_point_longest():
    assert find_point("足三里怎么按")[0] == "足三里"
    assert find_point("合谷穴在哪")[0] == "合谷"
    assert find_point("今天天气好") is None


def test_describe_has_where_for_how_caveat():
    s = describe("合谷")
    assert "虎口" in s and "头疼" in s and "按法" in s
    assert "保健不治病" in s and "孕妇" in s             # 免责与孕妇提醒都在
    assert "孕妇慎按" in s                                # 合谷特别标注
    assert describe("不存在穴") == ""


def test_for_symptom_recommends_points():
    s = for_symptom("头疼按哪个穴")
    assert "太阳穴" in s and "按摩" not in s.split("：")[0]
    assert "内关" in for_symptom("晕车按摩哪")
    assert "涌泉" in for_symptom("失眠按哪") or "神门" in for_symptom("失眠按哪")
    assert for_symptom("随便聊聊") == ""


def test_is_query_gating():
    assert is_acupoint_query("合谷穴在哪")
    assert is_acupoint_query("足三里怎么按")
    assert is_acupoint_query("头疼按哪个穴位")
    assert is_acupoint_query("失眠按摩哪")
    assert not is_acupoint_query("今天天气好")
    assert not is_acupoint_query("头有点疼")              # 只是难受、没问按哪 → 留给关怀/导诊


def test_config_extra_point():
    cfg = {"acupoints": {"points": {"百会": {"where": "头顶正中", "for": ["提神", "头晕"],
                                            "how": "指腹轻按", "note": ""}}}}
    assert "百会" in points(cfg)
    assert "头顶正中" in describe("百会", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ acupoints: all tests passed")
