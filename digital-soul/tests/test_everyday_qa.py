"""日常小问答测试。可直接运行：python tests/test_everyday_qa.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.everyday_qa import (  # noqa: E402
    answer, arithmetic, convert, date_query, zh2num,
)


def test_zh2num():
    assert zh2num("三") == 3 and zh2num("十") == 10
    assert zh2num("二十") == 20 and zh2num("二十三") == 23
    assert zh2num("15") == 15


def test_convert_weight():
    assert "1500克" in convert("三斤是多少克")
    assert convert("2公斤是几斤").startswith("2公斤是 4斤")
    assert convert("今天天气好") == ""


def test_convert_length():
    assert convert("1米等于多少厘米").startswith("1米是 100厘米")
    assert "500米" in convert("一里是多少米")


def test_arithmetic():
    assert arithmetic("三加五") == "等于 8。"
    assert arithmetic("十减四") == "等于 6。"
    assert arithmetic("六乘七") == "等于 42。"
    assert arithmetic("二十除以四") == "等于 5。"
    assert "不能是零" in arithmetic("五除以零")
    assert arithmetic("聊聊天") == ""


def test_date_query():
    now = datetime(2026, 6, 18, 9, 5)   # 2026-06-18 是星期四
    assert date_query("今天星期几", now) == "今天星期四。"
    assert "6 月 18 号" in date_query("今天几号", now)
    assert "9 点 5 分" in date_query("现在几点", now)


def test_answer_routes():
    assert "8" in answer("三加五")
    assert "克" in answer("三斤是多少克")
    assert answer("随便说点别的") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ everyday_qa: all tests passed")
