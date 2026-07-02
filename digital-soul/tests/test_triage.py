"""导诊分诊测试。可直接运行：python tests/test_triage.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.triage import (  # noqa: E402
    advise, count, departments, emergency_signs, find_department,
    is_triage_query,
)


def test_departments_present():
    ds = departments()
    assert "消化内科" in ds and "骨科" in ds and "眼科" in ds
    assert count() >= 15


def test_find_department_by_symptom():
    assert find_department("胃疼好几天了")[0] == "消化内科"
    assert find_department("膝盖关节痛")[0] == "骨科"
    assert find_department("血糖有点高")[0] == "内分泌科"
    assert find_department("牙疼")[0] == "口腔科"
    assert find_department("孩子发烧了")[0] in ("儿科", "发热门诊")  # 含「发烧」与「孩子」都可，最长匹配定夺
    assert find_department("今天天气好") is None


def test_emergency_signs_detected():
    assert emergency_signs("胸口压着疼")                     # 心梗样
    assert emergency_signs("突然半身没劲、说话不清")          # 中风
    assert emergency_signs("血流不止")                       # 大出血
    assert emergency_signs("胃有点胀") is None               # 普通不适不算急


def test_advise_emergency_says_120():
    s = advise("突然一侧胳膊抬不起、说话不清")
    assert "急诊" in s and "120" in s                        # 中风：直接喊急诊/120
    assert "别挂号" in s                                      # 明说别慢慢挂号等


def test_advise_department_has_disclaimer():
    s = advise("最近老咳嗽气短")
    assert "呼吸内科" in s
    assert "不是医生" in s and "120" in s                    # 留了免责与兜底


def test_advise_unknown_falls_back_to_general():
    s = advise("浑身没劲又说不上来哪儿")
    assert "全科" in s or "普通内科" in s


def test_is_triage_query_gating():
    assert is_triage_query("胃疼挂什么科")
    assert is_triage_query("头晕去医院看哪个科")
    assert is_triage_query("突然半身没劲说话不清")           # 危险信号：不带「看病」也要接住
    assert not is_triage_query("今天天气真好")
    assert not is_triage_query("我胃疼")                      # 只喊疼、没问就医意图 → 交给关怀路由


def test_config_extra_dept():
    cfg = {"triage": {"depts": [["疼痛科", ["浑身疼", "慢性疼痛"], "查不出原因的长期疼可挂疼痛科。"]]}}
    assert find_department("浑身疼好久了", cfg)[0] == "疼痛科"
    assert "疼痛科" in departments(cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ triage: all tests passed")
