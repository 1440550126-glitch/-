"""Obsidian 笔记格式测试。可直接运行：python tests/test_obsidian.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.obsidian import (  # noqa: E402
    add_link, append_section, hashtags, parse_note, render_note, set_section,
    slug, wikilinks,
)


def test_slug_strips_illegal():
    assert slug("A/B: C?*") == "AB C"
    assert slug("  回锅肉  ") == "回锅肉"
    assert slug("") == "未命名"


def test_wikilinks_and_tags():
    t = "聊到 [[川菜]] 和 [[妈|妈妈]]，#家常菜 #川菜 真香"
    assert wikilinks(t) == ["川菜", "妈"]               # |别名去掉、去重
    assert hashtags(t) == ["家常菜", "川菜"]


def test_render_has_frontmatter_links_tags():
    md = render_note("回锅肉", "二刀肉先煮再炒。", tags=["川菜"], links=["妈"],
                     aliases=["熬锅肉"], created="2026-06-25", source="对话")
    assert md.startswith("---")
    assert "title: 回锅肉" in md and "aliases: [熬锅肉]" in md
    assert "# 回锅肉" in md and "[[妈]]" in md and "#川菜" in md
    assert "source: 对话" in md


def test_parse_roundtrip():
    md = render_note("X", "正文", tags=["t1", "t2"], links=["A", "B"], created="2026-06-25")
    p = parse_note(md)
    assert p["title"] == "X"
    assert p["links"] == ["A", "B"]
    assert "t1" in p["tags"] and "t2" in p["tags"]
    assert "正文" in p["body"]
    assert p["frontmatter"]["created"] == "2026-06-25"


def test_parse_without_frontmatter():
    p = parse_note("# 裸标题\n一句话 [[链接]] #标签")
    assert p["title"] == "裸标题" and p["links"] == ["链接"] and "标签" in p["tags"]


def test_add_link_idempotent():
    md = render_note("X", "正文", links=["A"])
    md = add_link(md, "B")
    md = add_link(md, "A")          # 已存在
    links = wikilinks(md)
    assert links.count("A") == 1 and "B" in links


def test_add_link_creates_section():
    md = render_note("X", "正文")   # 没有关联区
    md = add_link(md, "新链接")
    assert "## 关联" in md and "[[新链接]]" in md


def test_append_section():
    md = render_note("X", "正文")
    md2 = append_section(md, "## 补记 2026-06-25", ["又想起一件事"])
    assert "## 补记" in md2 and "又想起一件事" in md2


def test_set_section_idempotent_and_anchored():
    md = render_note("小婷", "人物。", tags=["人物"], links=["回锅肉"])
    m1 = set_section(md, "## 小传", "她是我老婆。")
    # 插在关联区之前、标签还在
    assert m1.index("## 小传") < m1.index("## 关联")
    assert "#人物" in m1 and "[[回锅肉]]" in m1
    # 再设一次：替换不追加，仍只有一个小传
    m2 = set_section(m1, "## 小传", "她是我老婆，2018 年结的婚。")
    assert m2.count("## 小传") == 1 and "结的婚" in m2 and "[[回锅肉]]" in m2


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ obsidian: all tests passed")
