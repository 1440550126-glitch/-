"""老讲究/民俗测试。可直接运行：python tests/test_folk_customs.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.folk_customs import (  # noqa: E402
    count, customs, explain, find_custom, is_custom_query, recall,
)


def test_customs_present():
    cs = customs()
    for k in ("本命年穿红", "正月不剃头", "筷子不插饭上", "初一不扫地"):
        assert k in cs
    assert count() >= 8


def test_find_custom_trigger():
    assert find_custom("正月能剃头吗")[0] == "正月不剃头"
    assert find_custom("本命年要穿红吗")[0] == "本命年穿红"
    assert find_custom("筷子能插饭上吗")[0] == "筷子不插饭上"
    assert find_custom("今天天气好") is None


def test_explain_has_saying_and_view():
    s = explain("正月不剃头")
    assert "讹传" in s or "思旧" in s          # 说明这是误传
    assert len(s) > 15
    assert explain("不存在") == ""


def test_zhengyue_debunks_myth():
    # 正月剃头死舅舅应被点明是讹传，不吓唬人
    s = explain("正月不剃头")
    assert "不必当真" in s or "讹传" in s or "误传" in s


def test_recall_opens_topic():
    assert "老讲究" in recall(seed="z")


def test_is_query_gating():
    assert is_custom_query("本命年有啥讲究")
    assert is_custom_query("为什么初一不扫地")
    assert is_custom_query("聊聊老讲究")
    assert not is_custom_query("今天天气好")
    assert not is_custom_query("正月")            # 光提词、没问 → 不抢


def test_config_extra_custom():
    cfg = {"folk_customs": {"items": [["回门", ["回门", "三朝回门"], "新娘婚后头次回娘家叫回门",
                                       "图个两家亲热"]]}}
    assert "回门" in customs(cfg)
    assert find_custom("回门有啥讲究", cfg)[0] == "回门"
    assert "娘家" in explain("回门", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ folk_customs: all tests passed")
