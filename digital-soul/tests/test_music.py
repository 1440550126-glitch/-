"""老歌测试。可直接运行：python tests/test_music.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.music import (  # noqa: E402
    favorites, hum, is_music_request, song_for_mood,
)


def test_favorites_default_and_config():
    assert favorites() and "《茉莉花》" in favorites()
    assert favorites({"favorites": ["《我的歌》"]}) == ["《我的歌》"]


def test_hum():
    h = hum(seed="x")
    assert "哼起了" in h and "《" in h


def test_song_for_mood():
    assert "《" in song_for_mood("哀")
    s = song_for_mood("爱", {"by_mood": {"爱": ["《我俩的歌》"]}})
    assert "《我俩的歌》" in s
    assert "《" in song_for_mood("未知情绪")              # 回落到爱唱的歌


def test_is_music_request():
    assert is_music_request("给我唱首歌")
    assert is_music_request("哼一段呗")
    assert not is_music_request("几点了")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ music: all tests passed")
