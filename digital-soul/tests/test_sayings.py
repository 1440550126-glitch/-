"""口头语录测试。可直接运行：python tests/test_sayings.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.sayings import collect_sayings, pick_for, recite  # noqa: E402


def test_collect_merges_and_dedupes():
    sayings = {"sayings": ["家和万事兴", "做事要踏实"]}
    identity = {"personality": {"catchphrases": ["做事要踏实", "慢慢来"]}}
    out = collect_sayings(sayings, identity)
    assert out == ["家和万事兴", "做事要踏实", "慢慢来"]   # 去重、保序


def test_pick_for_topic():
    s = ["家和万事兴", "做事要踏实", "吃亏是福"]
    assert pick_for(s, "做事") == "做事要踏实"
    assert pick_for(s, None) == "家和万事兴"             # 无话题给第一句
    assert pick_for([], "x") is None


def test_recite():
    assert "「家和万事兴」" in recite(["家和万事兴", "做事要踏实"])
    assert recite([]) == ""


def test_agent_recite():
    a = object.__new__(Agent)
    a.sayings = {"sayings": ["家和万事兴"]}
    a.identity = {"personality": {"catchphrases": ["慢慢来"]}}
    s = a.recite_sayings()
    assert "家和万事兴" in s and "慢慢来" in s


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ sayings: all tests passed")
