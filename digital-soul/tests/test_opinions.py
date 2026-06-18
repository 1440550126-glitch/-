"""观点主张测试。可直接运行：python tests/test_opinions.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.opinions import (  # noqa: E402
    collect_opinions, is_opinion_query, match_topic, opine,
)

CFG = {"opinions": {"熬夜": "年轻人别老熬夜，身体是本钱",
                    "买房": "量力而行，别为一套房压垮自己"}}


def test_collect_merges_identity_list():
    idy = {"opinions": [{"topic": "存钱", "view": "手里有粮心里不慌"}]}
    o = collect_opinions(CFG, idy)
    assert o["熬夜"].startswith("年轻人")
    assert o["存钱"] == "手里有粮心里不慌"


def test_match_topic_longest():
    o = collect_opinions(CFG)
    assert match_topic(o, "你怎么看年轻人买房这事") == "买房"
    assert match_topic(o, "今天天气如何") is None


def test_is_opinion_query():
    assert is_opinion_query("你怎么看")
    assert is_opinion_query("你觉得熬夜好不好")
    assert not is_opinion_query("把灯关了")


def test_opine_consistent():
    o = collect_opinions(CFG)
    a = opine(o, "你怎么看熬夜")
    assert "熬夜" in a and "身体是本钱" in a
    assert opine(o, "你怎么看熬夜") == a                 # 前后一致
    assert opine(o, "你怎么看天气") == ""                # 没这话题就空


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ opinions: all tests passed")
