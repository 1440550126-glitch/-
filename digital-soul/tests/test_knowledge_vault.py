"""自生长知识库测试。可直接运行：python tests/test_knowledge_vault.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.knowledge_vault import Vault  # noqa: E402

N = "2026-06-25"


def _vault():
    return Vault(tempfile.mkdtemp(prefix="vault_"))


def test_grow_creates_note_on_disk():
    v = _vault()
    r = v.grow("川菜", "八大菜系之一。", tags=["菜系"], now=N)
    assert r["created"] is True and v.has("川菜")
    md = v.read("川菜")
    assert "# 川菜" in md and "#菜系" in md and "created: 2026-06-25" in md


def test_autolink_to_existing_notes():
    v = _vault()
    v.grow("川菜", "麻辣鲜香。", now=N)
    r = v.grow("回锅肉", "川菜名菜，先煮再炒。", now=N)
    assert "川菜" in r["auto_linked"]              # 正文提到已有的"川菜"→自动连链
    assert "川菜" in v.graph()["回锅肉"]


def test_no_self_link():
    v = _vault()
    r = v.grow("回锅肉", "回锅肉就是回锅肉。", links=["回锅肉"], now=N)
    assert "回锅肉" not in r["linked"]              # 不自链
    assert "回锅肉" not in v.graph().get("回锅肉", set())


def test_stub_created_for_dangling_link():
    v = _vault()
    r = v.grow("郫县豆瓣", "回锅肉的灵魂，见 [[豆瓣酱]]。", now=N)
    assert "豆瓣酱" in r["stubbed"] and v.has("豆瓣酱")
    assert "豆瓣酱" in v.stubs()
    assert "豆瓣酱" in v.graph()["郫县豆瓣"]


def test_backlinks_and_orphans():
    v = _vault()
    v.grow("A", "见 [[B]]。", now=N)
    v.grow("C", "孤零零一篇。", now=N)
    assert v.backlinks("B") == ["A"]
    assert "C" in v.orphans() and "A" not in v.orphans()


def test_grow_appends_on_second_call():
    v = _vault()
    v.grow("回锅肉", "第一段。", tags=["川菜"], now=N)
    r = v.grow("回锅肉", "第二段，关键郫县豆瓣。", tags=["家常菜"], now="2026-06-26")
    assert r["created"] is False
    md = v.read("回锅肉")
    assert "第一段" in md and "第二段" in md and "## 补记 2026-06-26" in md
    assert "#家常菜" in md and "updated: 2026-06-26" in md


def test_capture_derives_clean_title():
    v = _vault()
    r = v.capture("妈最拿手的就是 [[回锅肉]]，逢年过节必做。", tags=["妈"], now=N)
    assert "[[" not in r["title"] and "回锅肉" in r["linked"]
    assert r["title"] not in v.graph().get(r["title"], set())   # 没自链


def test_tag_index_and_suggest():
    v = _vault()
    v.grow("回锅肉", "经典。", tags=["川菜", "家常菜"], now=N)
    v.grow("麻婆豆腐", "也经典。", tags=["川菜"], now=N)
    ti = v.tag_index()
    assert set(ti["川菜"]) == {"回锅肉", "麻婆豆腐"}
    # 两篇共享 #川菜、还没互链 → 互相推荐
    assert "麻婆豆腐" in v.suggest_links("回锅肉")


def test_daily_note_appends():
    v = _vault()
    p1 = v.daily_note("聊了回锅肉", links=["回锅肉"], now=N)
    v.daily_note("又聊了麻婆豆腐", now=N)
    text = pathlib.Path(p1).read_text(encoding="utf-8")
    assert "聊了回锅肉" in text and "又聊了麻婆豆腐" in text and "[[回锅肉]]" in text


def test_consolidate_and_index():
    v = _vault()
    v.grow("回锅肉", "川菜，见 [[豆瓣酱]]。", tags=["川菜"], now=N)
    v.grow("麻婆豆腐", "川菜。", tags=["川菜"], now=N)
    c = v.consolidate()
    assert c["stats"]["notes"] >= 3 and "豆瓣酱" in c["stubs"]
    assert any("麻婆豆腐" in s for s in c["suggestions"].values())
    idx = v.build_index()
    assert "知识库总览" in idx and "#川菜" in idx and (v.root / "_index.md").exists()
    assert "_index" not in v.titles()             # 索引不算进笔记


def test_hubs_recent_and_people_gallery():
    from dsoul import memory_vault as mv
    v = _vault()
    v.grow("川菜", "回锅肉、麻婆豆腐都是川菜。", tags=["cuisines"], now=N)
    v.grow("回锅肉", "川菜名菜。", tags=["cuisines"], now=N)
    v.grow("麻婆豆腐", "川菜。", tags=["cuisines"], now="2026-06-26")
    mv.sediment_memories(v, ["我和小婷2018年认识", "小婷爱吃回锅肉"], [("小婷", "老婆")], now=N)
    # 枢纽：川菜被两篇连着，入度≥2
    hub_titles = [t for t, _n in v.hubs()]
    assert "川菜" in hub_titles
    # 最近：麻婆豆腐（更新日期最新）排在前面
    assert v.recent()[0] == "麻婆豆腐"
    # 人物廊：小婷有小传第一句
    assert "人物" in v.notes_with_tag("人物") or "小婷" in v.notes_with_tag("人物")
    assert "老婆" in v.bio_line("小婷")
    # 首页含人物廊 + 枢纽 + 知识脉络
    idx = v.build_index(now=N)
    assert "## 人物" in idx and "[[小婷]]" in idx and "条记忆" in idx
    assert "## 枢纽" in idx and "## 知识脉络" in idx


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ knowledge_vault: all tests passed")
