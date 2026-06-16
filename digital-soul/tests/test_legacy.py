"""编年生平 + 嘱托测试。可直接运行：python tests/test_legacy.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.legacy import chronicle, last_words, precepts  # noqa: E402

ITEMS = [
    {"text": "我家养了金毛豆豆", "when": "2021"},
    {"text": "我出生在四川成都", "when": "1990"},
    {"text": "我和小婷结婚了", "when": "2018"},
    {"text": "一个无年份的念头", "when": None},
    {"text": "梦见大海", "when": "2019", "tags": ["dream"]},   # 梦不算生平
]


def test_chronicle_is_ordered_first_person():
    c = chronicle(ITEMS)
    assert c.startswith("我这一生")
    i1990, i2018, i2021 = c.index("1990"), c.index("2018"), c.index("2021")
    assert i1990 < i2018 < i2021                      # 按年份升序
    assert "大海" not in c                             # 梦被排除


def test_chronicle_empty_when_no_dates():
    assert chronicle([{"text": "没有年份"}]) == ""


def test_last_words_and_precepts():
    legacy = {"last_words": ["好好吃饭", "别太拼"], "precepts": ["做人要诚实"]}
    assert last_words(legacy) == ["好好吃饭", "别太拼"]
    assert precepts(legacy) == ["做人要诚实"]
    assert last_words({}) == [] and precepts(None) == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ legacy: all tests passed")
