"""检查项目科普测试。可直接运行：python tests/test_medical_exams.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.medical_exams import (  # noqa: E402
    count, exams, find_exam, info, is_exam_query, overview,
)


def test_exams_present():
    es = exams()
    for k in ("B超", "X光", "CT", "核磁共振", "胃肠镜", "心电图"):
        assert k in es
    assert count() >= 7


def test_find_exam_alias():
    assert find_exam("彩超查什么") == "B超"
    assert find_exam("磁共振要注意") == "核磁共振"
    assert find_exam("做个胃镜") == "胃肠镜"
    assert find_exam("今天天气好") is None


def test_radiation_and_safety_notes():
    assert "无辐射" in info("B超")
    s = info("核磁共振")
    assert "起搏器" in s or "金属" in s                  # 核磁禁忌
    assert "造影剂" in info("CT") or "辐射" in info("CT")


def test_fasting_notes():
    assert "空腹" in info("抽血化验")
    assert "空腹" in info("胃肠镜") or "清肠" in info("胃肠镜")


def test_overview():
    o = overview()
    assert "B 超" in o and "核磁" in o and "心电图" in o


def test_is_query_gating():
    assert is_exam_query("B超查什么")
    assert is_exam_query("核磁共振有辐射吗")
    assert is_exam_query("胃镜疼吗")
    assert not is_exam_query("今天天气好")
    assert not is_exam_query("我做了个检查")             # 陈述、没问 → 不抢


def test_config_extra_exam():
    cfg = {"medical_exams": {"exams": {"骨密度": ["测骨质疏松程度", "无创、快"]}}}
    assert "骨密度" in exams(cfg)
    assert "骨质疏松" in info("骨密度", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ medical_exams: all tests passed")
