"""书信格式测试。可直接运行：python tests/test_letter_format.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.letter_format import (  # noqa: E402
    card_format, count, explain, find_part, is_letter_query, overview, parts,
)


def test_parts_present():
    ps = parts()
    for k in ("称呼", "问候语", "正文", "祝颂语", "署名", "日期"):
        assert k in ps
    assert count() >= 6


def test_find_part_alias():
    assert find_part("落款怎么写") == "署名"
    assert find_part("此致敬礼写哪") == "祝颂语"
    assert find_part("信封怎么写") == "信封"
    assert find_part("今天天气好") is None


def test_explain_salutation_and_closing():
    assert "顶格" in explain("称呼") and "冒号" in explain("称呼")
    s = explain("祝颂语")
    assert "此致" in s and "敬礼" in s


def test_card_and_overview():
    assert "称呼" in card_format() and "署名" in card_format()
    o = overview()
    assert "称呼" in o and "此致" in o and "署名" in o


def test_is_query_gating():
    assert is_letter_query("书信格式是什么")
    assert is_letter_query("称呼怎么写")
    assert is_letter_query("贺卡怎么写")
    assert not is_letter_query("今天天气好")
    assert not is_letter_query("给我写封信")          # 那是求代笔 → 归 letters，不抢


def test_config_extra_part():
    cfg = {"letter_format": {"parts": {"附言": "正文写完想起的补一句，写'又及:'或'P.S.'"}}}
    assert "附言" in parts(cfg)
    assert "又及" in explain("附言", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ letter_format: all tests passed")
