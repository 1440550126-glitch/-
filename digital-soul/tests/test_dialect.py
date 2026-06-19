"""乡音测试。可直接运行：python tests/test_dialect.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dialect import (  # noqa: E402
    demo,
    is_dialect_request,
    normalize_region,
    preset,
    region_in,
    regions,
    say_in,
    season,
    swap_words,
)


def test_regions_cover_main_areas():
    rs = regions()
    for r in ("四川", "东北", "北京", "广东", "上海"):
        assert r in rs


def test_normalize_region_aliases():
    assert normalize_region("川") == "四川"
    assert normalize_region("成都") == "四川"
    assert normalize_region("东北话") == "东北"
    assert normalize_region("广东话") == "广东"
    assert normalize_region("粤") == "广东"
    assert normalize_region("沪") == "上海"
    assert normalize_region("火星话") == ""


def test_say_in_concepts():
    assert say_in("四川", "yes") == "要得"
    assert say_in("东北", "good") == "老好了"
    assert say_in("上海", "yes") == "好额"
    assert say_in("广东", "thanks") == "唔该"
    assert say_in("火星", "yes") == ""


def test_swap_words_longest_first():
    # "干什么"应整体换成"嘎哈"，不被"什么"先吃成"啥"
    assert swap_words("你干什么呢", "东北") == "你嘎哈呢"
    assert swap_words("这是什么", "四川") == "这是啥子"
    assert swap_words("我不知道", "陕西") == "我知不道"


def test_season_level0_is_noop():
    assert season("你好啊。", "四川", level=0) == "你好啊。"
    assert season("你好", "火星", level=2) == "你好"          # 不认得就原样


def test_season_swaps_and_adds_particle():
    s = season("你知道吗。", "四川", level=2, seed="x")
    assert "晓得" in s                                       # 换了词
    # 末尾缀了语气词（在句号前）
    assert s.rstrip()[-1] == "。"
    assert any(p in s for p in ("嘛", "哈", "哦", "噻"))


def test_season_level1_swaps_only():
    s = season("你知道吗。", "四川", level=1)
    assert "晓得" in s
    assert not any(p in s.replace("晓得", "") for p in ("嘛", "噻"))  # 不强加语气词


def test_demo_nonempty_for_known():
    d = demo("东北")
    assert "中" in d and "东北" in d
    assert demo("火星") == ""


def test_region_in_detects():
    assert region_in("你用四川话说一句") == "四川"
    assert region_in("来段东北话") == "东北"
    assert region_in("说点粤语") == "广东" or region_in("说点广东话") == "广东"
    assert region_in("随便聊聊") == ""


def test_is_dialect_request():
    assert is_dialect_request("说句家乡话听听")
    assert is_dialect_request("用四川话怎么说")
    assert is_dialect_request("来一句东北话")
    assert is_dialect_request("来段东北话")
    assert is_dialect_request("说点上海话")
    assert is_dialect_request("讲讲方言")
    assert not is_dialect_request("今天天气怎么样")
    assert not is_dialect_request("我去过广东")          # 提到地名但不是要听方言


def test_preset_is_copy():
    p = preset("四川")
    p["yes"] = "改坏"
    assert say_in("四川", "yes") == "要得"                    # 内部数据没被改


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dialect: all tests passed")
