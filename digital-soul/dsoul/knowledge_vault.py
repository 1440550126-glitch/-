"""自生长知识库（Claude × Obsidian）：分身把学到的、聊到的知识，一篇篇写成 Obsidian 笔记，
自动连成知识图谱，越长越大、越连越密——你随时能用 Obsidian 打开它、看那张图。

"自生长"体现在：
  · 写新笔记时，自动把正文里提到的"已有笔记"连成 [[双链]]（图谱自己长起来）；
  · 给出的 [[链接]] 若还没这篇，自动建一篇"待充实"的桩，保持图谱连通；
  · 反向链接 / 标签索引 / 孤岛检测 / 关联建议 / 总览 MOC，定期"整理"让它更有序。

落地为一个目录里的 .md 文件（本地优先、可入 Obsidian、可 git）。
渲染/解析用 obsidian.py（零依赖）。IO 很薄，纯逻辑都可单测；时间 now 可注入。
"""

from __future__ import annotations

import pathlib

from . import obsidian as ob

_DAILY_DIR = "日记"
_INDEX = "_index.md"
_STUB = "（待充实）"


def _today(now=None) -> str:
    if now is None:
        from datetime import date
        return date.today().isoformat()
    if hasattr(now, "isoformat"):
        s = now.isoformat()
        return s[:10]
    return str(now)[:10]


class Vault:
    """一座知识库（一个目录）。"""

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------- 基础 IO ----------
    def path_for(self, title) -> pathlib.Path:
        return self.root / f"{ob.slug(title)}.md"

    def has(self, title) -> bool:
        return self.path_for(title).exists()

    def read(self, title) -> str | None:
        p = self.path_for(title)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def _write(self, title, md) -> None:
        self.path_for(title).write_text(md, encoding="utf-8")

    def _note_files(self) -> list:
        """所有"主笔记"文件（不含 _index、不含日记）。"""
        return [p for p in self.root.glob("*.md") if p.name != _INDEX]

    def titles(self) -> list:
        out = []
        for p in self._note_files():
            try:
                t = ob.parse_note(p.read_text(encoding="utf-8"))["title"] or p.stem
            except Exception:
                t = p.stem
            out.append(t)
        return out

    def note(self, title) -> dict | None:
        md = self.read(title)
        return ob.parse_note(md) if md is not None else None

    def aliases_index(self) -> dict:
        """别名/标题 → 规范标题，给自动连链用。"""
        idx = {}
        for p in self._note_files():
            try:
                pn = ob.parse_note(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            t = pn["title"] or p.stem
            idx[t] = t
            al = pn["frontmatter"].get("aliases")
            for a in (al if isinstance(al, list) else []):
                idx[str(a)] = t
        return idx

    # ---------- 自生长：写 / 长 ----------
    def grow(self, title, body="", *, tags=(), links=(), source="",
             now=None, autolink=True) -> dict:
        """长一篇笔记：没有就新建、有就把新内容并进去；自动连链、自动给新链接建桩。"""
        title = str(title).strip()
        if not title:
            return {"ok": False, "reason": "empty title"}
        today = _today(now)
        tags = list(dict.fromkeys(str(t) for t in tags if str(t).strip()))
        links = list(dict.fromkeys(str(x) for x in links if str(x).strip()))

        # 自动连链：正文里提到的"别的已有笔记"，连上 [[双链]]
        auto = []
        if autolink and body:
            for name, canon in self.aliases_index().items():
                if canon == title or len(name) < 2:
                    continue
                if name in str(body) and canon not in links and canon not in auto:
                    auto.append(canon)
        all_links = [x for x in dict.fromkeys(links + auto) if x != title]  # 不自链

        created_now = not self.has(title)
        if created_now:
            md = ob.render_note(title, body, tags=tags, links=all_links,
                                created=today, updated=today, source=source)
        else:
            md = self.read(title)
            pn = ob.parse_note(md)
            # 并入新正文（带日期小节）、合并标签、补链接
            if body:
                md = ob.append_section(md, f"## 补记 {today}", [body])
            for lk in all_links:
                md = ob.add_link(md, lk)
            cur_tags = pn["tags"]
            new_tags = [t for t in tags if t not in cur_tags]
            if new_tags:
                md = md.rstrip("\n") + "\n\n" + " ".join(f"#{t}" for t in new_tags) + "\n"
            md = _bump_updated(md, today)
        self._write(title, md)

        # 给还不存在的链接建"待充实"的桩，保持图谱连通（含正文里写的 [[双链]]）
        stub_targets = [x for x in dict.fromkeys(all_links + (ob.wikilinks(body) if body else []))
                        if x != title]
        stubbed = []
        for lk in stub_targets:
            if not self.has(lk):
                self._write(lk, ob.render_note(lk, _STUB, created=today, updated=today,
                                               source=f"由[[{title}]]带出"))
                stubbed.append(lk)
        return {"ok": True, "title": title, "created": created_now,
                "linked": all_links, "auto_linked": auto, "stubbed": stubbed}

    def capture(self, text, *, title=None, tags=(), source="", now=None) -> dict:
        """从一段话里"捕获"成一篇笔记：标题没给就从话里取；自动带上话里的 #标签 和 [[链接]]。"""
        text = str(text or "").strip()
        if not text:
            return {"ok": False, "reason": "empty"}
        in_tags = list(tags) + [t for t in ob.hashtags(text) if t not in tags]
        in_links = ob.wikilinks(text)
        if not title:
            # 第一小句当标题：去掉 [[双链]]/#标签 的语法、只留文字，截短
            import re
            first = re.split(r"[。！？，、\.!?\n]", text, 1)[0].strip()
            first = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", r"\1", first)
            first = re.sub(r"#[0-9A-Za-z一-鿿_\-/]+", "", first).strip()
            title = first[:24] or ("速记 " + _today(now))
        return self.grow(title, text, tags=in_tags, links=in_links, source=source, now=now)

    def link(self, a, b, *, bidir=True, now=None) -> dict:
        """手动连两篇（不存在就建桩）。"""
        r1 = self.grow(a, "", links=[b], now=now)
        if bidir:
            self.grow(b, "", links=[a], now=now)
        return r1

    def daily_note(self, line, *, date=None, links=(), now=None) -> str:
        """把一句记进当天的日记笔记（自生长的"流水"入口）。"""
        d = date or _today(now)
        ddir = self.root / _DAILY_DIR
        ddir.mkdir(exist_ok=True)
        p = ddir / f"{d}.md"
        links = list(links)
        bullet = "- " + str(line).strip() + ("".join(f" [[{x}]]" for x in links) if links else "")
        if p.exists():
            p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + bullet + "\n", encoding="utf-8")
        else:
            p.write_text(f"# {d}\n\n{bullet}\n", encoding="utf-8")
        return str(p)

    # ---------- 图谱 ----------
    def graph(self) -> dict:
        """标题 → 它指向的笔记集合（出链）。"""
        g = {}
        for p in self._note_files():
            try:
                pn = ob.parse_note(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            g[pn["title"] or p.stem] = set(pn["links"])
        return g

    def backlinks(self, title) -> list:
        """谁连向了这篇（反向链接）。"""
        title = str(title)
        return sorted(t for t, outs in self.graph().items() if title in outs)

    def orphans(self) -> list:
        """孤岛：既没人连它、它也不连别人的笔记。"""
        g = self.graph()
        incoming = set()
        for outs in g.values():
            incoming |= outs
        return sorted(t for t, outs in g.items() if not outs and t not in incoming)

    def stubs(self) -> list:
        """还没充实的桩笔记。"""
        out = []
        for p in self._note_files():
            try:
                if _STUB in p.read_text(encoding="utf-8"):
                    out.append(ob.parse_note(p.read_text(encoding="utf-8"))["title"] or p.stem)
            except Exception:
                pass
        return sorted(out)

    def tag_index(self) -> dict:
        """标签 → 带该标签的笔记标题。"""
        idx = {}
        for p in self._note_files():
            try:
                pn = ob.parse_note(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            t = pn["title"] or p.stem
            for tag in pn["tags"]:
                idx.setdefault(tag, [])
                if t not in idx[tag]:
                    idx[tag].append(t)
        return {k: sorted(v) for k, v in idx.items()}

    def suggest_links(self, title, limit=5) -> list:
        """给某篇笔记荐几条"也许该连"的：共享标签 / 互相提到名字、但还没连上的。"""
        me = self.note(title)
        if not me:
            return []
        my_tags = set(me["tags"])
        my_text = (me["body"] or "")
        linked = set(me["links"]) | {title}
        scored = []
        for p in self._note_files():
            try:
                pn = ob.parse_note(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            t = pn["title"] or p.stem
            if t in linked:
                continue
            score = len(my_tags & set(pn["tags"]))
            if t in my_text:                      # 我正文里提到了它
                score += 2
            if title in (pn["body"] or ""):       # 它正文里提到了我
                score += 1
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [t for _s, t in scored[:limit]]

    def consolidate(self, now=None) -> dict:
        """整理一遍：孤岛、桩、给每篇的关联建议、统计。"""
        titles = self.titles()
        suggestions = {}
        for t in titles:
            s = self.suggest_links(t, limit=3)
            if s:
                suggestions[t] = s
        return {
            "orphans": self.orphans(),
            "stubs": self.stubs(),
            "suggestions": suggestions,
            "stats": self.stats(),
        }

    def stats(self) -> dict:
        g = self.graph()
        edges = sum(len(o) for o in g.values())
        return {"notes": len(g), "links": edges, "tags": len(self.tag_index()),
                "orphans": len(self.orphans()), "stubs": len(self.stubs())}

    def notes_with_tag(self, tag) -> list:
        """带某个标签的笔记标题（如所有 #人物）。"""
        return self.tag_index().get(str(tag), [])

    def hubs(self, limit=8) -> list:
        """枢纽：被连得最多的笔记（入度高 = 核心概念）。返回 [(标题, 入度)]。"""
        g = self.graph()
        indeg = {}
        for outs in g.values():
            for t in outs:
                indeg[t] = indeg.get(t, 0) + 1
        ranked = sorted(((t, n) for t, n in indeg.items() if t in g),
                        key=lambda x: (-x[1], x[0]))
        return [(t, n) for t, n in ranked[:limit] if n >= 2]

    def recent(self, limit=8) -> list:
        """最近更新的笔记（按 frontmatter.updated 倒序）。返回标题列表。"""
        rows = []
        for p in self._note_files():
            try:
                pn = ob.parse_note(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            t = pn["title"] or p.stem
            up = str(pn["frontmatter"].get("updated") or pn["frontmatter"].get("created") or "")
            rows.append((up, t))
        rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [t for _u, t in rows[:limit]]

    def bio_line(self, name) -> str:
        """某人物的小传第一句（给首页人物廊做摘要）。没有返回空。"""
        md = self.read(name)
        if md is None:
            return ""
        return ob.first_sentence(ob.get_section(md, "## 小传"))

    def build_index(self, now=None) -> str:
        """写一篇 _index.md 首页（MOC）：概况 + 人物廊 + 枢纽 + 知识脉络 + 最近 + 待打理。
        让这座自生长知识库有个能一眼看见"它长成什么样"的门面。"""
        st = self.stats()
        people = self.notes_with_tag("人物")
        mem_notes = set(self.notes_with_tag("记忆"))
        lines = ["# 知识库总览", "",
                 f"> 共 **{st['notes']}** 篇 · {st['links']} 条链接 · {st['tags']} 个标签 · "
                 f"{len(people)} 个人物 · {st['orphans']} 座孤岛 · {st['stubs']} 篇待充实", ""]

        # 人物廊：每个人 + 小传第一句 + 记忆条数
        if people:
            lines.append("## 人物")
            for t in people:
                bl = len([b for b in self.backlinks(t) if b in mem_notes])
                bio = self.bio_line(t)
                tail = f"（{bl} 条记忆）" if bl else ""
                lines.append(f"- [[{t}]]{tail}" + (f"：{bio}" if bio else ""))
            lines.append("")

        # 枢纽：被连得最多的核心概念
        hubs = self.hubs()
        if hubs:
            lines += ["## 枢纽（连得最多的）",
                      "、".join(f"[[{t}]]（{n}）" for t, n in hubs), ""]

        # 知识脉络：按标签（人物/记忆有自己的区，这里不重复列）
        ti = self.tag_index()
        knowledge_tags = [tag for tag in sorted(ti) if tag not in ("人物", "记忆")]
        if knowledge_tags:
            lines.append("## 知识脉络")
            for tag in knowledge_tags:
                refs = "、".join(f"[[{t}]]" for t in ti[tag])
                lines.append(f"- **#{tag}**：{refs}")
            lines.append("")

        # 最近
        rec = self.recent()
        if rec:
            lines += ["## 最近", "、".join(f"[[{t}]]" for t in rec), ""]

        # 待打理：孤岛 + 桩
        orph, stub = self.orphans(), self.stubs()
        if orph or stub:
            lines.append("## 待打理")
            if orph:
                lines.append("- 孤岛（还没连上的）：" + "、".join(f"[[{t}]]" for t in orph))
            if stub:
                lines.append("- 待充实：" + "、".join(f"[[{t}]]" for t in stub))
            lines.append("")

        md = "\n".join(lines).rstrip() + "\n"
        (self.root / _INDEX).write_text(md, encoding="utf-8")
        return md


def _bump_updated(md, today) -> str:
    """把 frontmatter 的 updated 改成今天（没有就算了）。"""
    import re
    if "updated:" in md:
        return re.sub(r"(?m)^updated:.*$", f"updated: {today}", md, count=1)
    return md
