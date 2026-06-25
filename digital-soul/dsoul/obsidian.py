"""Obsidian 笔记格式（纯逻辑、零依赖、可单测）：渲染 / 解析 Obsidian 风格的 markdown——
YAML frontmatter（title/aliases/tags/created/updated/source）、`[[双链]]`、`#标签`、关联区。

这是"自生长知识库"的底座：把一条知识变成一篇能在 Obsidian 里打开、能连成图谱的笔记。
不引 pyyaml，自己处理用到的那几种简单 frontmatter（标量 + 简单列表）。
"""

from __future__ import annotations

import re

_ILLEGAL = r'[\\/:*?"<>|#^\[\]]'      # 文件名里不能有的字符
_WIKILINK = re.compile(r"\[\[([^\[\]|]+?)(?:\|[^\[\]]*)?\]\]")
_HASHTAG = re.compile(r"(?<![0-9A-Za-z一-鿿_])#([0-9A-Za-z一-鿿_\-/]+)")
_LINKS_HEADING = "## 关联"


def slug(title: str) -> str:
    """把标题变成安全的文件名基名（保留中文与空格，去掉非法字符）。"""
    s = re.sub(_ILLEGAL, "", str(title or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s or "未命名"


def wikilinks(text: str) -> list:
    """抽出文本里的 [[双链]] 目标（去掉 |别名，去重保序）。"""
    out, seen = [], set()
    for m in _WIKILINK.finditer(str(text or "")):
        t = m.group(1).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def hashtags(text: str) -> list:
    """抽出文本里的 #标签（去重保序，不含 # ）。"""
    out, seen = [], set()
    for m in _HASHTAG.finditer(str(text or "")):
        t = m.group(1)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _emit_frontmatter(fm: dict) -> str:
    lines = ["---"]
    for k, v in fm.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, (list, tuple)):
            inner = ", ".join(str(x) for x in v)
            lines.append(f"{k}: [{inner}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _parse_scalar_list(val: str):
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return [x.strip() for x in inner.split(",") if x.strip()] if inner else []
    return val


def render_note(title, body="", *, tags=(), links=(), aliases=(),
                created=None, updated=None, source="", extra=None) -> str:
    """渲染一篇 Obsidian 笔记：frontmatter + 正文 + 关联区（[[双链]]）+ 行内 #标签。"""
    fm = {
        "title": str(title),
        "aliases": list(aliases),
        "tags": list(tags),
        "created": created or "",
        "updated": updated or created or "",
        "source": source or "",
    }
    if isinstance(extra, dict):
        for k, v in extra.items():
            fm[str(k)] = v
    parts = [_emit_frontmatter(fm), "", f"# {title}", ""]
    if body:
        parts.append(str(body).rstrip())
        parts.append("")
    links = [str(x) for x in links if str(x).strip()]
    if links:
        parts.append(_LINKS_HEADING)
        parts.extend(f"- [[{t}]]" for t in links)
        parts.append("")
    if tags:
        parts.append(" ".join(f"#{t}" for t in tags))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def parse_note(md: str) -> dict:
    """解析一篇笔记 → {frontmatter, title, body, links, tags}。容错：没有 frontmatter 也能读。"""
    text = str(md or "")
    fm: dict = {}
    body_text = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip("\n")
            body_text = text[end + 4:].lstrip("\n")
            for line in block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = _parse_scalar_list(v.strip())
    # 标题：frontmatter.title 优先，否则第一个 # 标题
    title = fm.get("title")
    if not title:
        m = re.search(r"^#\s+(.+)$", body_text, re.M)
        title = m.group(1).strip() if m else ""
    links = wikilinks(text)
    tags = list(fm.get("tags") or []) if isinstance(fm.get("tags"), list) else []
    for t in hashtags(text):
        if t not in tags:
            tags.append(t)
    return {"frontmatter": fm, "title": title, "body": body_text, "links": links, "tags": tags}


def add_link(md: str, target: str) -> str:
    """把一条 [[target]] 加进笔记的关联区（已存在则原样返回；没有关联区就新建）。幂等。"""
    target = str(target or "").strip()
    if not target:
        return md
    if target in wikilinks(md):
        return md
    text = str(md or "").rstrip("\n")
    line = f"- [[{target}]]"
    if _LINKS_HEADING in text:
        # 插到关联区标题后（紧跟其它链接）
        idx = text.index(_LINKS_HEADING) + len(_LINKS_HEADING)
        nl = text.find("\n", idx)
        if nl == -1:
            return text + "\n" + line + "\n"
        return text[:nl + 1] + line + "\n" + text[nl + 1:] + "\n" if not text.endswith("\n") else \
            text[:nl + 1] + line + "\n" + text[nl + 1:]
    return text + f"\n\n{_LINKS_HEADING}\n{line}\n"


def append_section(md: str, heading: str, lines) -> str:
    """在笔记末尾追加一段（自生长时把新内容并进已有笔记）。"""
    text = str(md or "").rstrip("\n")
    body = "\n".join(f"{x}" for x in (lines if isinstance(lines, (list, tuple)) else [lines]))
    return text + f"\n\n{heading}\n{body}\n"
