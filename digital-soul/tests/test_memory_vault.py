"""记忆入库测试。可直接运行：python tests/test_memory_vault.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul import memory_vault as mv  # noqa: E402
from dsoul.knowledge_vault import Vault  # noqa: E402

N = "2026-06-25"


def _vault():
    return Vault(tempfile.mkdtemp(prefix="mem_"))


def test_people_in_longest_match():
    names = ["小婷", "婷", "张爸"]
    got = mv.people_in("我和小婷散步，张爸在家。", names)
    assert "小婷" in got and "张爸" in got and "婷" not in got    # 长名优先、不被子串误伤


def test_memory_title_clean():
    assert mv.memory_title("我答应小婷退休带她去看极光。") == "答应小婷退休带她去看极光"
    # 长句断在词边界，不切碎数字
    t = mv.memory_title("我和小婷是在大学篮球场认识的，2018年结婚。")
    assert "2018" not in t and t.startswith("和小婷")
    assert mv.memory_title("") == "一段记忆"


def test_ensure_person_creates_and_tags():
    v = _vault()
    assert mv.ensure_person(v, "小婷", "妻子", now=N) is True
    assert v.has("小婷") and "#人物" in v.read("小婷") and "妻子" in v.read("小婷")
    assert mv.ensure_person(v, "小婷", now=N) is False           # 已存在


def test_sediment_memories_links_people():
    v = _vault()
    mems = [
        "我答应小婷，等退休了带她去看一次极光。",
        "我家有只金毛叫豆豆，特别黏小婷。",
    ]
    rep = mv.sediment_memories(v, mems, [("小婷", "妻子"), ("豆豆", "狗")], now=N)
    assert len(rep["memory_notes"]) == 2
    assert "小婷" in rep["person_notes"] and "豆豆" in rep["person_notes"]
    # 小婷这篇人物笔记被两条记忆连着（越连越懂这个人）
    assert len(v.backlinks("小婷")) == 2
    assert "#人物" in v.read("小婷") and "#记忆" in v.read(rep["memory_notes"][0])


def test_memory_note_has_wikilink():
    v = _vault()
    rep = mv.sediment_memories(v, ["我答应小婷去看极光。"], ["小婷"], now=N)
    md = v.read(rep["memory_notes"][0])
    assert "[[小婷]]" in md


def test_dedup_same_memory():
    v = _vault()
    mv.sediment_memories(v, ["我答应小婷去看极光。"], ["小婷"], now=N)
    rep2 = mv.sediment_memories(v, ["我答应小婷去看极光。"], ["小婷"], now="2026-06-26")
    assert rep2["touched"] == []                                 # 同一条不重复


def test_daily_note_written():
    v = _vault()
    mv.sediment_memories(v, ["我答应小婷去看极光。"], ["小婷"], now=N)
    daily = v.root / "日记" / f"{N}.md"
    assert daily.exists() and "巩固了这些记忆" in daily.read_text(encoding="utf-8")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ memory_vault: all tests passed")
