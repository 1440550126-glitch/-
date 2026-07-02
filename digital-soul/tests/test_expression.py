"""神态测试。可直接运行：python tests/test_expression.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.expression import (  # noqa: E402
    describe_face,
    emoji_for,
    emotions,
    face_for,
    led_color,
)


def test_face_for_known():
    f = face_for("喜")
    assert "上扬" in f["mouth"]
    assert f["color"][1].startswith("#") and len(f["color"][1]) == 7
    assert f["emoji"]


def test_face_for_unknown_defaults_neutral():
    f = face_for("莫名其妙")
    assert f["color"][0] == "柔白"               # 回落到平和
    assert face_for(None)["emoji"] == "🙂"


def test_describe_face():
    s = describe_face("哀")
    assert "（" in s and "光）" in s
    assert "黯淡" in s or "下撇" in s


def test_led_color_distinct():
    assert led_color("喜") != led_color("哀")
    assert led_color("怒")[1] == "#C9544B"


def test_emoji_for():
    assert emoji_for("乐") == "😄"
    assert emoji_for("爱") == "🥰"


def test_emotions_list_excludes_neutral():
    es = emotions()
    assert "喜" in es and "哀" in es
    assert "中" not in es


def test_face_is_copy():
    f = face_for("喜")
    f["mouth"] = "改坏了"
    assert "上扬" in face_for("喜")["mouth"]      # 内部数据不被改


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ expression: all tests passed")
