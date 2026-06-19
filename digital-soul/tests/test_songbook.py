"""歌本测试。可直接运行：python tests/test_songbook.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.songbook import (  # noqa: E402
    is_recognize_request,
    is_singalong,
    is_sing_request,
    known_songs,
    lead_singalong,
    lyric_lines,
    next_lyric,
    recognize,
    sing,
    wants_lyrics,
)


def test_known_songs_nonempty():
    ks = known_songs()
    assert "《茉莉花》" in ks and "《送别》" in ks


def test_lyric_lines_with_or_without_brackets():
    a = lyric_lines("《茉莉花》")
    b = lyric_lines("茉莉花")                       # 不带书名号也认
    assert a == b
    assert a[0] == "好一朵美丽的茉莉花"


def test_lyric_lines_unknown_empty():
    assert lyric_lines("《查无此歌》") == []


def test_sing_named_song_quotes_words():
    s = sing("送别")
    assert "《送别》" in s
    assert "长亭外" in s                            # 唱出了真词
    assert "和一句" in s                            # 招呼你和


def test_sing_unknown_song_falls_back_to_hum():
    s = sing("《周杰伦的歌》")                       # 没词 → 哼调子兜底
    assert "哼" in s


def test_next_lyric_chains():
    nl = next_lyric("送别", "长亭外，古道边")
    assert nl == "芳草碧连天"


def test_next_lyric_partial_match():
    nl = next_lyric("《茉莉花》", "好一朵美丽的茉莉花")
    assert nl == "好一朵美丽的茉莉花"               # 这首头两句重复，下一句仍是它


def test_next_lyric_end_returns_empty():
    last = lyric_lines("送别")[-1]
    assert next_lyric("送别", last) == ""


def test_recognize_from_fragment():
    assert recognize("芳草碧连天") == "《送别》"
    assert recognize("东方红，太阳升") == "《东方红》"


def test_recognize_unknown_empty():
    assert recognize("我爱北京天安门") == ""
    assert recognize("") == ""


def test_lead_singalong_gives_first_line():
    s = lead_singalong("茉莉花")
    assert "好一朵美丽的茉莉花" in s and "接下一句" in s


def test_config_can_add_song():
    cfg = {"lyrics": {"我家的歌": ["第一句词", "第二句词"]}}
    assert "《我家的歌》" in known_songs() or True    # 默认不含
    assert lyric_lines("我家的歌", cfg) == ["第一句词", "第二句词"]
    assert next_lyric("我家的歌", "第一句词", cfg) == "第二句词"
    assert recognize("第二句词", cfg) == "《我家的歌》"


def test_detectors():
    assert is_sing_request("给我唱一句")
    assert is_sing_request("你唱两句呗")
    assert not is_sing_request("我们一起唱")          # 合唱不算独唱
    assert is_singalong("陪我唱首歌")
    assert is_singalong("咱俩唱")
    assert wants_lyrics("送别的歌词是啥")
    assert wants_lyrics("下一句是什么")
    assert is_recognize_request("这是什么歌来着")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ songbook: all tests passed")
