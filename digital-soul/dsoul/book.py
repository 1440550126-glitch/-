"""家族册：比单页纪念册更厚的一本——每位家人各有一页（生平要点、性格、口头禅、
TA 的记忆），再附一段家人对谈。完全离线、自包含（无外链、无脚本），可打印成 PDF 传家。

纯逻辑、零第三方依赖、可单测。Agent.build_family_book() 取数后调用本模块拼装。
"""

from __future__ import annotations

from .keepsake import _esc


def member_section(member, memories=None) -> str:
    """一位家人的一页：称呼、一句话、性格、口头禅、TA 的记忆。"""
    name = member.get("name", "TA")
    rel = member.get("relation", "")
    head = f"{_esc(name)}" + (f" · {_esc(rel)}" if rel else "")
    parts = [f'<h2>{head}</h2>']
    if member.get("summary"):
        parts.append(f'<p class="lead">{_esc(member["summary"])}</p>')
    traits = member.get("traits") or []
    if traits:
        parts.append('<p class="traits">' +
                     "".join(f'<span class=chip>{_esc(t)}</span>' for t in traits) + "</p>")
    cps = member.get("catchphrases") or []
    if cps:
        parts.append('<p class="say">常挂嘴边：' +
                     "　".join(f"「{_esc(c)}」" for c in cps) + "</p>")
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if mems:
        parts.append("<ul class=mems>" +
                     "".join(f"<li>{_esc(m)}</li>" for m in mems) + "</ul>")
    if not member.get("summary") and not traits and not cps and not mems:
        parts.append('<p class="dim">这一页还很空，等你慢慢添。</p>')
    return '<section class="member">' + "".join(parts) + "</section>"


def dialogue_section(turns) -> str:
    """一段家人对谈（[{speaker,text}, …]）排成对话。"""
    turns = [t for t in (turns or []) if t.get("speaker") and t.get("text")]
    if not turns:
        return ""
    rows = "".join(
        f'<div class=turn><b>{_esc(t["speaker"])}</b>：{_esc(t["text"])}</div>' for t in turns)
    return f'<section><h2>那天，他们这样聊着</h2>{rows}</section>'


def family_book_html(title, members_sections, family_line="", dialogue="") -> str:
    """把封面 + 各位家人页 + 对谈拼成一本自包含 HTML。"""
    title = title or "我们家"
    cover_sub = _esc(family_line) if family_line else "一家人的样子"
    body = "".join(members_sections) + dialogue
    if not body.strip():
        body = '<section><p class="dim">还没登记家人（见 config/family.yaml）。</p></section>'
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{_esc(title)} · 家族册</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:"Songti SC","STSong",Georgia,"Noto Serif SC",serif;color:#2b2b2b;
background:#ece3d6;margin:0;padding:26px 14px;line-height:1.85}}
.book{{max-width:700px;margin:0 auto;background:#fbf7f0;border:1px solid #e4dac9;
border-radius:6px;padding:42px 40px;box-shadow:0 8px 40px rgba(80,60,30,.12)}}
.cover{{text-align:center;padding:30px 0 12px;border-bottom:2px solid #cdb88a;margin-bottom:18px}}
.cover .seal{{font-size:34px;color:#9a7b3f}}
.cover h1{{font-size:32px;letter-spacing:.12em;margin:.2em 0}}
.cover .sub{{color:#9a7b3f;letter-spacing:.28em;font-size:14px}}
section.member{{break-inside:avoid;padding:14px 0;border-bottom:1px dashed #e0d6c4}}
h2{{font-size:20px;color:#7a5c2a;letter-spacing:.06em}}
.lead{{font-size:16px}}
.traits .chip{{display:inline-block;background:#f0e7d4;color:#7a5c2a;border-radius:999px;
padding:2px 12px;margin:3px 6px 3px 0;font-size:13px}}
.say{{color:#9a7b3f}}
ul.mems{{margin:6px 0 0;padding-left:20px}} ul.mems li{{margin:4px 0}}
.turn{{margin:5px 0;padding-left:10px;border-left:3px solid #d8c69a}}
.dim{{color:#9b9b9b}}
.foot{{text-align:center;color:#aa9c80;font-size:12px;margin-top:30px;letter-spacing:.2em}}
@media print{{body{{background:#fff;padding:0}}.book{{box-shadow:none;border:none}}
section.member{{page-break-inside:avoid}}}}
</style></head>
<body><div class=book>
<div class=cover><div class=seal>❦</div><h1>{_esc(title)}</h1>
<div class=sub>{cover_sub}</div></div>
{body}
<div class=foot>本册完全离线生成 · 可打印 · 可传家</div>
</div></body></html>"""
