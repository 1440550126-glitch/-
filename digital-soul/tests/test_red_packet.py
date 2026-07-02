"""红包祝词/吉利数测试。可直接运行：python tests/test_red_packet.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.red_packet import (  # noqa: E402
    advise, count, find_occasion, is_red_packet_query, lucky_amounts,
    lucky_meaning, occasions, words_for,
)


def test_occasions_present():
    occ = occasions()
    for k in ("压岁钱", "婚礼", "生日", "乔迁", "升学"):
        assert k in occ
    assert count() >= 6


def test_find_occasion_alias():
    assert find_occasion("随份子包多少") == "婚礼"
    assert find_occasion("过年红包写啥") == "压岁钱"
    assert find_occasion("搬家送红包") == "乔迁"
    assert find_occasion("今天天气好") is None


def test_lucky_meaning():
    assert lucky_meaning(888) == "发发发"
    assert lucky_meaning(1314) == "一生一世"
    assert lucky_meaning(666) == "六六大顺"
    assert lucky_meaning(777) == ""             # 没收录的数字


def test_words_and_amounts():
    assert words_for("婚礼", seed="a")
    amts = lucky_amounts("婚礼")
    nums = [a for a, _ in amts]
    assert 888 in nums and 1314 in nums
    assert all(m for _, m in amts)              # 每个数都有寓意说明


def test_advise_full():
    s = advise("婚礼", seed="x")
    assert "封面" in s and "888" in s and "量力而行" in s
    assert "忌单数" in s or "双数" in s          # 婚礼忌讳提醒在
    assert advise("不存在场合") == ""


def test_is_query_gating():
    assert is_red_packet_query("过年红包写啥")
    assert is_red_packet_query("婚礼份子钱包多少吉利")
    assert is_red_packet_query("压岁钱给多少合适")
    assert not is_red_packet_query("今天天气好")
    assert not is_red_packet_query("送了个红包")   # 陈述、没问写啥/多少 → 不抢


def test_config_extra_occasion():
    cfg = {"red_packet": {"occasions": {"探病": {"words": ["早日康复"], "amounts": [600], "note": "探病心意为主"}}}}
    assert "探病" in occasions(cfg)
    assert "早日康复" in advise("探病", config=cfg)
    assert lucky_amounts("探病", cfg)[0][0] == 600


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ red_packet: all tests passed")
