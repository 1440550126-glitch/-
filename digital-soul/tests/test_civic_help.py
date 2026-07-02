"""办事指南测试。可直接运行：python tests/test_civic_help.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.civic_help import (  # noqa: E402
    count, find_matter, how_to, is_civic_query, matters,
)


def test_matters_present():
    ms = matters()
    for k in ("身份证", "社保卡", "敬老卡", "医保异地", "护照"):
        assert k in ms
    assert count() >= 7


def test_find_matter_alias():
    assert find_matter("老年卡怎么办") == "敬老卡"
    assert find_matter("异地就医怎么备案") == "医保异地"
    assert find_matter("房本过户") == "房产证"
    assert find_matter("今天天气好") is None


def test_how_to_has_where_bring_caveat():
    s = how_to("身份证")
    assert "派出所" in s and "户口本" in s
    assert "12345" in s and "代办" in s             # 通用提醒：12345 + 防代办
    assert how_to("不存在") == ""


def test_id_card_lost_flow():
    s = how_to("身份证")
    assert "挂失" in s or "异地受理" in s


def test_is_query_gating():
    assert is_civic_query("身份证丢了怎么补")
    assert is_civic_query("社保卡在哪办")
    assert is_civic_query("异地就医怎么报销")
    assert not is_civic_query("今天天气好")
    assert not is_civic_query("我带了身份证")        # 陈述、没问怎么办 → 不抢


def test_config_extra_matter():
    cfg = {"civic_help": {"matters": {"居住证": ["到居住地派出所或社区办，带身份证和居住证明", "满半年可办"]}}}
    assert "居住证" in matters(cfg)
    assert how_to("居住证", cfg).startswith("办居住证：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ civic_help: all tests passed")
