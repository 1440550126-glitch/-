"""体检报告解读测试。可直接运行：python tests/test_checkup.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.checkup import (  # noqa: E402
    count, direction, find_item, interpret, is_checkup_query, items,
)


def test_items_present():
    its = items()
    for k in ("血压", "尿酸", "空腹血糖", "低密度脂蛋白", "谷丙转氨酶", "体重指数"):
        assert k in its
    assert count() >= 14


def test_find_item_alias_and_longest():
    assert find_item("尿酸高")[0] == "尿酸"
    assert find_item("ALT偏高")[0] == "谷丙转氨酶"          # 缩写别名
    assert find_item("坏胆固醇高")[0] == "低密度脂蛋白"      # 俗称别名
    assert find_item("低密度脂蛋白高")[0] == "低密度脂蛋白"  # 别被「低密度」短词截掉
    assert find_item("今天天气好") is None


def test_direction_detection():
    assert direction("尿酸偏高") == "high"
    assert direction("血红蛋白低") == "low"
    assert direction("血糖正常吗") == ""


def test_interpret_high_low_overall():
    s = interpret("尿酸高是什么意思")
    assert "尿酸偏高" in s and "痛风" in s and "听医生" in s   # 含义 + 免责
    lo = interpret("血红蛋白低")
    assert "贫血" in lo
    overall = interpret("BMI是什么意思")
    assert "体重指数" in overall and "正常正常" not in overall  # 不重复「正常」
    assert interpret("今天吃啥") == ""                        # 没指标 → 空
    # 指标名自带「高/低」字，别把名字里的字当成箭头方向
    assert interpret("低密度脂蛋白高").startswith("低密度脂蛋白偏高：")
    assert interpret("高密度脂蛋白低").startswith("高密度脂蛋白偏低：")
    # 没说方向（只说「有箭头」）→ 走整体解读，而不是被名字里的「低」带成偏低
    s2 = interpret("体检报告上低密度脂蛋白有箭头")
    assert s2.startswith("低密度脂蛋白：") and "偏低：" not in s2


def test_is_checkup_query_gating():
    assert is_checkup_query("看看我的体检报告")
    assert is_checkup_query("尿酸高是什么意思")
    assert is_checkup_query("转氨酶偏高怎么回事")
    assert not is_checkup_query("今天天气真好")
    assert not is_checkup_query("血压计在哪")                 # 提到血压但不是解读意图


def test_config_extra_item():
    cfg = {"checkup": {"items": [{"name": "同型半胱氨酸", "alias": ["Hcy"],
                                  "normal": "约 <15 μmol/L", "high": "偏高与心脑血管风险相关，补叶酸有帮助",
                                  "low": "偏低无碍", "tip": "高了问医生要不要补叶酸 B 族。"}]}}
    assert "同型半胱氨酸" in items(cfg)
    assert find_item("Hcy偏高", cfg)[0] == "同型半胱氨酸"
    assert "叶酸" in interpret("同型半胱氨酸高", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ checkup: all tests passed")
