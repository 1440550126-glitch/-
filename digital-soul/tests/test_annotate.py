"""情感标注 + 时间抽取测试。可直接运行：python tests/test_annotate.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.annotate import classify_emotion, extract_when  # noqa: E402


def test_joy():
    assert classify_emotion("今天特别开心，笑得合不拢嘴")["label"] == "喜悦"


def test_sadness():
    assert classify_emotion("外婆去世了，我很难过，哭了一整晚")["label"] == "悲伤"


def test_love():
    assert classify_emotion("我会守护我老婆一辈子")["label"] == "深情"


def test_nostalgia():
    assert classify_emotion("小时候那年夏天，我们在河里游泳")["label"] == "怀念"


def test_neutral():
    assert classify_emotion("把文件放在桌子上")["label"] == "平静"


def test_extract_year():
    assert extract_when("我们2018年结婚") == "2018"
    assert extract_when("我1990年出生") == "1990"
    assert extract_when("没有年份的一句话") is None


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("PASS", _name)
    print("✅ annotate: all tests passed")
