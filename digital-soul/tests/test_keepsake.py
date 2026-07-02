"""数字纪念册测试。可直接运行：python tests/test_keepsake.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.keepsake import (build_keepsake, gather_photos,  # noqa: E402
                            keepsake_html, timeline_groups)

_PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

ITEMS = [
    {"text": "在成都出生", "when": "1990"},
    {"text": "和小婷结婚", "when": "2018"},
    {"text": "养了金毛豆豆", "when": "2021"},
    {"text": "梦见大海", "when": "2019", "tags": ["dream"]},   # 梦不进纪念册
    {"text": "没有年份的念头", "when": None},
]


def test_timeline_groups_sorted_no_dreams():
    g = timeline_groups(ITEMS)
    years = [y for y, _ in g]
    assert years == ["1990", "2018", "2021"]               # 升序、排除梦与无年份
    assert all("大海" not in t for _, ts in g for t in ts)


def test_keepsake_html_is_selfcontained_and_complete():
    h = keepsake_html("外公", chronicle="我这一生……",
                      last_words=["好好吃饭", " "], precepts=["做人要诚实"],
                      family="咱家有：外公、外婆。", timeline=timeline_groups(ITEMS))
    assert h.startswith("<!doctype html>") and h.rstrip().endswith("</html>")
    assert "外公" in h and "我这一生" in h and "做人要诚实" in h
    assert "「好好吃饭」" in h and "1990" in h and "外婆" in h
    assert "http://" not in h and "https://" not in h      # 自包含：无外链
    assert "<script" not in h                              # 无脚本
    assert "「 」" not in h                                  # 空白嘱托被过滤


def test_keepsake_escapes_html():
    h = keepsake_html("<b>x</b>", chronicle="a<script>b")
    assert "<b>x</b>" not in h and "&lt;b&gt;" in h
    assert "<script>b" not in h


def test_empty_keepsake_degrades():
    h = keepsake_html("TA")
    assert "还没攒下" in h and h.startswith("<!doctype html>")


def test_photos_embedded_selfcontained():
    photos = [{"src": "data:image/png;base64,AAAA", "caption": "1990 出生"}]
    h = keepsake_html("外公", photos=photos)
    assert "影像" in h and "<figure>" in h
    assert 'src="data:image/png;base64,AAAA"' in h
    assert "1990 出生" in h
    assert "http://" not in h and "https://" not in h     # 仍自包含
    assert "影像" not in keepsake_html("外公")               # 无照片则无该节


def test_gather_photos_reads_folder():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / "b_2018.png").write_bytes(_PNG)
        (d / "a_1990.png").write_bytes(_PNG)
        (d / "notes.txt").write_text("x", encoding="utf-8")
        got = gather_photos(d)
        assert [p["caption"] for p in got] == ["a_1990", "b_2018"]   # 排序、跳过非图片
        assert all(p["src"].startswith("data:image/png;base64,") for p in got)
        assert gather_photos(d / "nope") == []                      # 不存在 → 空


class _Agent:
    identity = {"name": "张明"}
    legacy = {"last_words": ["别太拼"], "precepts": ["多回家"]}
    family = {"members": [{"name": "外婆", "relation": "姥姥"}]}

    class _M:
        items = ITEMS
    memory = _M()

    def life_chronicle(self):
        return "我这一生平平淡淡。"


def test_build_keepsake_from_agent():
    h = build_keepsake(_Agent())
    assert "张明" in h and "平平淡淡" in h
    assert "别太拼" in h and "多回家" in h and "外婆" in h and "2018" in h


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ keepsake: all tests passed")
