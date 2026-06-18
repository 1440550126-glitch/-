"""老来的宽慰测试。可直接运行：python tests/test_dignity.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dignity import reassure_dignity, senses_aging_worry  # noqa: E402


def test_senses_aging_worry():
    assert senses_aging_worry("我老了，怕给你们添麻烦")
    assert senses_aging_worry("人老了不中用喽")
    assert senses_aging_worry("记性越来越差，老忘事")
    assert not senses_aging_worry("今天天气真好")


def test_reassure_dignity_tailored():
    a = reassure_dignity("我怕成了你们的累赘", name="妈")
    assert a.startswith("妈，") and "该轮到我们疼你" in a
    assert "定海神针" in reassure_dignity("我老了没用了")
    assert "替你记着" in reassure_dignity("我记性越来越差")


def test_no_match_empty():
    assert reassure_dignity("今天吃了饭") == ""


def test_present_tense_no_death_words():
    for u in ("怕成累赘", "老了没用", "老忘事", "怕孤独老去"):
        r = reassure_dignity(u)
        for bad in ("死", "走了", "不在了", "临终"):
            assert bad not in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dignity: all tests passed")
