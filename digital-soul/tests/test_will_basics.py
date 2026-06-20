"""立遗嘱常识测试。可直接运行：python tests/test_will_basics.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.will_basics import (  # noqa: E402
    advice, count, find_topic, is_will_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("自书遗嘱", "公证遗嘱", "见证人", "遗嘱内容", "注意事项"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("手写遗嘱有效吗") == "自书遗嘱"
    assert find_topic("遗嘱有几种") == "遗嘱形式"
    assert find_topic("找谁做见证人") == "见证人"
    assert find_topic("今天天气好") is None


def test_self_written_requirements():
    s = advice("自书遗嘱")
    assert "亲笔" in s and "签名" in s and "年" in s     # 全文手写+签名+日期
    assert "不能打印" in s or "打印" in s
    assert "律师" in s or "公证" in s                     # 免责尾巴


def test_witness_restrictions():
    s = advice("见证人")
    assert "两个" in s and "继承人" in s and "利害关系" in s


def test_overview_mentions_notary():
    o = overview()
    assert "公证遗嘱" in o and "自书" in o and "律师" in o


def test_is_query_gating():
    assert is_will_query("遗嘱怎么写才有效")
    assert is_will_query("自书遗嘱要注意什么")
    assert is_will_query("立遗嘱有用吗")
    assert not is_will_query("今天天气好")


def test_config_extra_topic():
    cfg = {"will_basics": {"topics": {"遗赠扶养": ["和愿意养老送终的人签协议、把财产给他", "需书面、可公证"]}}}
    assert "遗赠扶养" in topics(cfg)
    assert "协议" in advice("遗赠扶养", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ will_basics: all tests passed")
