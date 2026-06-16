"""数字纪念册：把一个人的一生导出成一页可保存、可打印、可分享的 HTML。

完全离线、自包含（样式内联，无外链、无脚本、无网络），是"数字遗产"的纸面那一版——
TA 的编年生平、想留给你的话、家训、这一家子、一生时间线，安安静静收在一页里。
纯逻辑、零第三方依赖、可单测。
"""

from __future__ import annotations

import base64
import html as _html
import mimetypes
from pathlib import Path


def _esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _image_data_uri(path) -> str | None:
    """把一张图片读成自包含的 data: URI（base64），让纪念册离线也带得走。"""
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    if not mime.startswith("image/"):
        return None
    try:
        return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return None


def gather_photos(folder, limit: int = 24) -> list:
    """扫一个文件夹里的图片，按文件名排序，文件名（去后缀）作为图注。"""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    out = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            uri = _image_data_uri(f)
            if uri:
                out.append({"src": uri, "caption": f.stem})
        if len(out) >= limit:
            break
    return out


def timeline_groups(items, people=None) -> list:
    """把带年份、非梦境的记忆按年份聚合：[(年, [文本, …]), …]，升序。"""
    by_year: dict[str, list] = {}
    for it in items or []:
        w = it.get("when")
        if not (w and str(w).isdigit()):
            continue
        if "dream" in (it.get("tags") or []):
            continue
        by_year.setdefault(str(w), []).append(it.get("text", ""))
    return [(y, by_year[y]) for y in sorted(by_year, key=int)]


def keepsake_html(name, chronicle="", last_words=None, precepts=None,
                  family="", timeline=None, subtitle=None, photos=None) -> str:
    """渲染一页自包含的纪念册 HTML（可直接存成 .html 双击打开 / 打印成 PDF）。"""
    name = name or "TA"
    last_words = [w for w in (last_words or []) if str(w).strip()]
    precepts = [p for p in (precepts or []) if str(p).strip()]
    timeline = timeline or []
    photos = [p for p in (photos or []) if p.get("src")]
    sub = subtitle if subtitle is not None else "一生的回响 · 数字纪念册"

    def section(title, body):
        return f'<section><h2>{_esc(title)}</h2>{body}</section>' if body else ""

    chron_html = f'<p class="chron">{_esc(chronicle)}</p>' if chronicle else ""
    lw_html = ("<ul class=quotes>" + "".join(f"<li>「{_esc(w)}」</li>" for w in last_words)
               + "</ul>") if last_words else ""
    pc_html = ("<ul class=quotes>" + "".join(f"<li>「{_esc(p)}」</li>" for p in precepts)
               + "</ul>") if precepts else ""
    fam_html = f'<p class="fam">{_esc(family)}</p>' if family else ""
    ph_html = ""
    if photos:
        cells = "".join(
            f'<figure><img src="{p["src"]}" alt=""><figcaption>{_esc(p.get("caption", ""))}'
            f'</figcaption></figure>' for p in photos)
        ph_html = f'<div class=gallery>{cells}</div>'
    tl_html = ""
    if timeline:
        rows = []
        for year, texts in timeline:
            items = "".join(f"<div class=tlitem>{_esc(t)}</div>" for t in texts)
            rows.append(f'<div class=tlyear>{_esc(year)}</div>{items}')
        tl_html = '<div class=timeline>' + "".join(rows) + "</div>"

    body = "".join([
        section("TA 的一生", chron_html),
        section("影像", ph_html),
        section("想留给你的话", lw_html),
        section("家训", pc_html),
        section("这一家子", fam_html),
        section("一生时间线", tl_html),
    ]) or '<section><p class="dim">还没攒下可以编成纪念册的内容。</p></section>'

    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{_esc(name)} · 数字纪念册</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:"Songti SC","STSong",Georgia,"Noto Serif SC",serif;color:#2b2b2b;
background:#efe7da;margin:0;padding:28px 14px;line-height:1.85}}
.book{{max-width:680px;margin:0 auto;background:#fbf7f0;border:1px solid #e6ded2;
border-radius:6px;padding:44px 40px;box-shadow:0 8px 40px rgba(80,60,30,.12)}}
.crest{{text-align:center;color:#9a7b3f;font-size:30px;margin-bottom:6px}}
h1{{text-align:center;font-size:30px;margin:.2em 0;letter-spacing:.08em}}
.sub{{text-align:center;color:#9a7b3f;font-size:14px;letter-spacing:.3em;margin-bottom:8px}}
.rule{{width:64px;height:2px;background:#9a7b3f;margin:18px auto 26px;opacity:.7}}
section{{margin:26px 0}}
h2{{font-size:18px;color:#9a7b3f;border-bottom:1px solid #e6ded2;padding-bottom:6px;
letter-spacing:.12em}}
.chron{{font-size:16px;text-indent:2em;white-space:pre-wrap}}
.fam{{font-size:16px}}
.quotes{{list-style:none;padding:0}}
.quotes li{{font-size:17px;margin:10px 0;padding-left:14px;border-left:3px solid #d8c69a}}
.timeline{{margin-top:6px}}
.tlyear{{color:#9a7b3f;font-weight:700;margin:14px 0 4px;font-size:15px}}
.tlitem{{margin:3px 0 3px 18px;position:relative;color:#3a3a3a;font-size:15px}}
.tlitem:before{{content:"·";position:absolute;left:-12px;color:#c9b896}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin-top:8px}}
figure{{margin:0;background:#fff;padding:8px 8px 4px;border:1px solid #e6ded2;
box-shadow:0 2px 8px rgba(80,60,30,.1)}}
figure img{{width:100%;height:auto;display:block;filter:sepia(.12)}}
figcaption{{text-align:center;color:#9a7b3f;font-size:12px;padding:6px 0 2px}}
.dim{{color:#9b9b9b}}
.foot{{text-align:center;color:#aa9c80;font-size:12px;margin-top:34px;letter-spacing:.2em}}
@media print{{body{{background:#fff;padding:0}}.book{{box-shadow:none;border:none}}}}
</style></head>
<body><div class=book>
<div class=crest>🕯️</div>
<h1>{_esc(name)}</h1>
<div class=sub>{_esc(sub)}</div>
<div class=rule></div>
{body}
<div class=foot>本页完全离线生成 · 可保存 · 可打印留存</div>
</div></body></html>"""


def build_keepsake(agent, photos_dir=None) -> str:
    """从 agent 取数，渲染整本纪念册；photos_dir 里的图片会自包含地嵌进"影像"。"""
    name = agent.identity.get("name", "TA") if getattr(agent, "identity", None) else "TA"
    chronicle = ""
    if hasattr(agent, "life_chronicle"):
        try:
            chronicle = agent.life_chronicle()
        except Exception:
            chronicle = ""
    last_words, precepts = [], []
    try:
        from .legacy import last_words as _lw, precepts as _pc
        last_words = _lw(getattr(agent, "legacy", {}) or {})
        precepts = _pc(getattr(agent, "legacy", {}) or {})
    except Exception:
        pass
    family = ""
    if getattr(agent, "family", None):
        try:
            from .family import roster_line
            family = roster_line(agent.family)
        except Exception:
            family = ""
    items = agent.memory.items if getattr(agent, "memory", None) is not None else []
    photos = gather_photos(photos_dir) if photos_dir else []
    return keepsake_html(name, chronicle=chronicle, last_words=last_words,
                         precepts=precepts, family=family,
                         timeline=timeline_groups(items), photos=photos)
