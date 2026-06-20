"""看懂药品说明书测试。可直接运行：python tests/test_drug_label.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.drug_label import (  # noqa: E402
    count, explain, find_section, is_drug_label_query, overview, sections,
)


def test_sections_present():
    ss = sections()
    for k in ("适应症", "用法用量", "不良反应", "禁忌", "OTC标志"):
        assert k in ss
    assert count() >= 8


def test_find_section_alias():
    assert find_section("副作用是啥") == "不良反应"
    assert find_section("功能主治写啥") == "适应症"
    assert find_section("处方药什么标志") == "OTC标志"
    assert find_section("今天天气好") is None


def test_explain_key_sections():
    assert "对症" in explain("适应症")
    assert "绝对不能用" in explain("禁忌")               # 禁忌最要紧
    s = explain("OTC标志")
    assert "红色" in s and "绿色" in s and ("处方" in s or "Rx" in s)


def test_overview_lists_key_sections():
    o = overview()
    assert "适应症" in o and "用法用量" in o and "禁忌" in o
    assert "问药师" in o


def test_is_query_gating():
    assert is_drug_label_query("说明书上适应症是什么")
    assert is_drug_label_query("不良反应啥意思")
    assert is_drug_label_query("药品说明书怎么看")
    assert not is_drug_label_query("今天天气好")
    assert not is_drug_label_query("我吃了药")           # 陈述、不是问说明书 → 不抢


def test_config_extra_section():
    cfg = {"drug_label": {"sections": {"药物过量": "吃多了会怎样、怎么处理，严重打 120"}}}
    assert "药物过量" in sections(cfg)
    assert "120" in explain("药物过量", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ drug_label: all tests passed")
