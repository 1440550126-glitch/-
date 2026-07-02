"""生活谣言辟谣测试。可直接运行：python tests/test_debunk.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.debunk import (  # noqa: E402
    count, find_myth, is_myth_query, myths, recall, truth,
)


def test_myths_present():
    ms = myths()
    for k in ("隔夜菜致癌", "喝醋软化血管", "酸碱体质", "木耳久泡", "保健品治病"):
        assert k in ms
    assert count() >= 10


def test_find_myth_trigger():
    assert find_myth("隔夜菜致癌吗")[0] == "隔夜菜致癌"
    assert find_myth("喝醋能软化血管吗")[0] == "喝醋软化血管"
    assert find_myth("今天天气好") is None


def test_truth_balanced():
    # 纯谣言要破
    assert "伪科学" in truth("酸碱体质")
    assert "没用" in truth("喝醋软化血管")
    # 有道理的要当真（木耳久泡确有风险）
    t = truth("木耳久泡")
    assert "当真" in t and ("米酵菌酸" in t or "现泡现吃" in t)
    assert truth("不存在") == ""


def test_leftovers_nuanced():
    # 隔夜菜不致癌，但绿叶菜亚硝酸盐要提醒——别一刀切
    t = truth("隔夜菜致癌")
    assert "不会" in t and "绿叶菜" in t


def test_supplement_dont_stop_meds():
    t = truth("保健品治病")
    assert "不是药" in t and ("停" in t and "药" in t)


def test_recall_opens_topic():
    assert "谣" in recall(seed="y")


def test_is_query_gating():
    assert is_myth_query("隔夜菜致癌吗")
    assert is_myth_query("酸碱体质是真的吗")
    assert is_myth_query("保健品能治病吗")
    assert not is_myth_query("今天天气好")
    assert not is_myth_query("我喝了点醋")              # 陈述、没求证 → 不抢


def test_config_extra_myth():
    cfg = {"debunk": {"items": [["疫苗有害", ["疫苗有害", "打疫苗"], "正规疫苗经严格验证，按程序接种利大于弊"]]}}
    assert "疫苗有害" in myths(cfg)
    assert "利大于弊" in truth("疫苗有害", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ debunk: all tests passed")
