"""居家适老改造测试。可直接运行：python tests/test_elder_proofing.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.elder_proofing import (  # noqa: E402
    areas, checklist, count, find_area, is_proofing_query, suggest,
)


def test_areas_present():
    a = areas()
    for k in ("卫生间", "卧室", "客厅过道", "楼梯门口"):
        assert k in a
    assert count() >= 5


def test_find_area_alias():
    assert find_area("浴室怎么防摔改造") == "卫生间"
    assert find_area("起夜摔倒") == "卧室"
    assert find_area("地毯绊脚") == "客厅过道"
    assert find_area("今天天气好") is None


def test_bathroom_has_grab_bars():
    s = suggest("卫生间")
    assert "扶手" in s and "防滑" in s


def test_bedroom_night_light():
    s = suggest("卧室")
    assert "小夜灯" in s or "夜里" in s


def test_checklist_core_three():
    c = checklist()
    assert "卫生间" in c and "防摔" in c and "呼救" in c


def test_is_query_gating():
    assert is_proofing_query("卫生间怎么适老改造")
    assert is_proofing_query("卧室怎么防摔")
    assert is_proofing_query("适老化改造有哪些")
    assert not is_proofing_query("今天天气好")
    assert not is_proofing_query("我家有卫生间")     # 陈述、没问改造 → 不抢


def test_config_extra_area():
    cfg = {"elder_proofing": {"areas": {"阳台": ["护栏加高、地面防滑、别堆杂物", "晾衣杆放低些"]}}}
    assert "阳台" in areas(cfg)
    assert "护栏" in suggest("阳台", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ elder_proofing: all tests passed")
