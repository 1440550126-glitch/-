"""家族病史测试。可直接运行：python tests/test_health_history.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.health_history import (  # noqa: E402
    advice_for, allergy_line, allergy_of, collect_conditions, health_warning,
    hereditary, people_with,
)

CFG = {
    "conditions": [
        {"who": "你太爷", "condition": "高血压", "note": "五十岁上得的，别贪咸"},
        {"who": "你爸", "condition": "高血压"},
        {"who": "你奶奶", "condition": "糖尿病", "note": "甜食要忌口"},
    ],
    "allergies": [{"who": "小明", "to": "花生"}, {"who": "小明", "to": "海鲜"}],
}


def test_collect_and_hereditary():
    conds = collect_conditions(CFG)
    assert len(conds) == 3
    assert hereditary(conds) == ["高血压"]               # 出现两次
    assert people_with(conds, "高血压") == ["你太爷", "你爸"]
    assert advice_for(conds, "高血压") == ["五十岁上得的，别贪咸"]


def test_health_warning_hereditary():
    s = health_warning(collect_conditions(CFG))
    assert "高血压" in s and "会遗传" in s and "别贪咸" in s


def test_health_warning_no_hereditary():
    cfg = {"conditions": [{"who": "你爸", "condition": "胃病"}]}
    s = health_warning(collect_conditions(cfg))
    assert "胃病" in s and "留个心" in s
    assert health_warning([]) == ""


def test_allergies():
    assert set(allergy_of(CFG, "小明")) == {"花生", "海鲜"}
    assert allergy_of(CFG, "陌生人") == []
    line = allergy_line(CFG, "小明")
    assert "小明" in line and "花生" in line and "过敏" in line
    assert allergy_line(CFG, "没这人") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ health_history: all tests passed")
