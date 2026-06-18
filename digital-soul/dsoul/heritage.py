"""传家页（家珍册）：把分身替这个家守着的念想，汇成一张本地静态网页——
家谱、遗物、家史故事、做人道理与手艺、口头语录、家传菜、家族病史、人情往来、遗言家训。
一页翻完，是这一家的来路与念想。纯逻辑生成 HTML、可单测、零网络。

scripts/heritage.py 生成到 data/heritage.html，浏览器打开即可。
"""

from __future__ import annotations

from html import escape


def heritage_data(agent) -> dict:
    """汇总传家内容；每一块各自降级，任意取数失败不影响其余。"""
    def _try(fn, default):
        try:
            return fn()
        except Exception:
            return default

    def _gene():
        from .genealogy import build_tree, by_generation
        tree = build_tree(getattr(agent, "family", {}) or {})
        return [{"label": lb, "names": ns} for lb, ns in by_generation(tree)]

    def _heir():
        from .heirloom import collect_heirlooms
        return collect_heirlooms(getattr(agent, "heirlooms", None), getattr(agent, "legacy", None))

    def _health():
        from .health_history import allergies, collect_conditions
        return {"conditions": collect_conditions(getattr(agent, "health", None)),
                "allergies": allergies(getattr(agent, "health", None))}

    def _stories():
        from .storytelling import collect_stories
        mem = agent.memory.items if getattr(agent, "memory", None) else []
        return collect_stories(getattr(agent, "stories", None), mem)

    def _teach():
        from .teaching import collect_lessons, collect_skills
        return {"lessons": collect_lessons(getattr(agent, "teachings", None)),
                "skills": collect_skills(getattr(agent, "teachings", None))}

    def _say():
        from .sayings import collect_sayings
        return collect_sayings(getattr(agent, "sayings", None), getattr(agent, "identity", None))

    def _rec():
        from .recipes import collect_recipes, list_names
        return list_names(collect_recipes(getattr(agent, "recipes", None), getattr(agent, "family", None)))

    def _fav():
        fav = getattr(agent, "favors", None)
        if fav is None:
            return {"we_owe": [], "they_owe": []}
        return {"we_owe": fav.we_owe(), "they_owe": fav.they_owe()}

    def _legacy():
        from .legacy import last_words, precepts
        leg = getattr(agent, "legacy", {}) or {}
        return {"last_words": last_words(leg), "precepts": precepts(leg)}

    def _mann():
        from .mannerisms import describe
        return describe(getattr(agent, "mannerisms", None))

    return {
        "name": (getattr(agent, "identity", {}) or {}).get("name", "TA"),
        "genealogy": _try(_gene, []),
        "heirlooms": _try(_heir, []),
        "health": _try(_health, {"conditions": [], "allergies": []}),
        "stories": _try(_stories, []),
        "teachings": _try(_teach, {"lessons": [], "skills": []}),
        "sayings": _try(_say, []),
        "recipes": _try(_rec, []),
        "favors": _try(_fav, {"we_owe": [], "they_owe": []}),
        "legacy": _try(_legacy, {"last_words": [], "precepts": []}),
        "mannerisms": _try(_mann, ""),
    }


def _section(title, inner) -> str:
    """一张卡片；inner 为空则整块略去（不展示空板块）。"""
    if not inner:
        return ""
    return f'<section class=card><h2>{escape(title)}</h2>{inner}</section>'


def _ul(items) -> str:
    items = [escape(str(x)) for x in items if str(x).strip()]
    return ("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>") if items else ""


def heritage_html(data) -> str:
    """把 heritage_data 渲染成一张静态网页。"""
    data = data or {}
    name = escape(str(data.get("name", "TA")))
    blocks = []

    # 家谱
    gene = data.get("genealogy") or []
    if gene:
        rows = "".join(
            f'<div class=genrow><span class=genlab>{escape(g["label"])}</span>'
            f'<span class=gennames>{escape("、".join(g["names"]))}</span></div>'
            for g in gene)
        blocks.append(_section("👪 家谱", rows))

    # 遗言 / 家训
    leg = data.get("legacy") or {}
    leg_inner = ""
    if leg.get("last_words"):
        leg_inner += "<div class=k>想留给你的话</div>" + _ul(leg["last_words"])
    if leg.get("precepts"):
        leg_inner += "<div class=k>家训</div>" + _ul(leg["precepts"])
    blocks.append(_section("💌 遗言与家训", leg_inner))

    # 故事
    stories = data.get("stories") or []
    if stories:
        items = "".join(
            f'<div class=story><div class=stitle>{escape(s["title"] or "往事")}</div>'
            f'<div class=sbody>{escape(s["story"])}</div></div>' for s in stories)
        blocks.append(_section("📖 家史与往事", items))

    # 教导：道理 + 手艺
    teach = data.get("teachings") or {}
    teach_inner = ""
    if teach.get("lessons"):
        teach_inner += "<div class=k>做人的道理</div><ul>" + "".join(
            f'<li>{escape((l["topic"] + "：") if l["topic"] else "")}{escape(l["lesson"])}</li>'
            for l in teach["lessons"]) + "</ul>"
    if teach.get("skills"):
        for sk in teach["skills"]:
            steps = "；".join(sk["steps"]) if sk.get("steps") else "（手把手示范）"
            teach_inner += (f'<div class=k>🔧 {escape(sk["name"])}</div>'
                            f'<div class=sbody>{escape(steps)}</div>')
    blocks.append(_section("🎓 言传身教", teach_inner))

    # 遗物
    heir = data.get("heirlooms") or []
    if heir:
        items = ""
        for it in heir:
            meta = "，".join(x for x in [
                (f'{it["from"]}传下' if it.get("from") else ""),
                (f'{it["year"]}年' if it.get("year") else ""),
                (f'给{it["to"]}' if it.get("to") else ""),
                (f'收在{it["where"]}' if it.get("where") else "")] if x)
            items += (f'<div class=story><div class=stitle>{escape(it["item"])}'
                      f'<span class=dim>　{escape(meta)}</span></div>'
                      f'<div class=sbody>{escape(it.get("story", ""))}</div></div>')
        blocks.append(_section("🧧 遗物信物", items))

    # 家传菜 + 语录 + 口头习惯
    blocks.append(_section("🍲 家传菜", _ul(data.get("recipes") or [])))
    blocks.append(_section("🗣️ 口头语录", _ul(data.get("sayings") or [])))
    blocks.append(_section("💬 说话的习惯", f"<p>{escape(data['mannerisms'])}</p>"
                           if data.get("mannerisms") else ""))

    # 家族病史
    health = data.get("health") or {}
    h_inner = ""
    if health.get("conditions"):
        h_inner += "<ul>" + "".join(
            f'<li>{escape(c["who"])}：{escape(c["condition"])}'
            f'{("（" + escape(c["note"]) + "）") if c.get("note") else ""}</li>'
            for c in health["conditions"]) + "</ul>"
    if health.get("allergies"):
        h_inner += "<div class=k>过敏</div>" + _ul(
            f'{a["who"]} 忌 {a["to"]}' for a in health["allergies"])
    blocks.append(_section("🩺 家族病史", h_inner))

    # 人情往来
    fav = data.get("favors") or {}
    f_inner = ""
    if fav.get("we_owe"):
        f_inner += "<div class=k>咱还欠的人情</div>" + _ul(
            f"{p}（{a}）" for p, a in fav["we_owe"])
    if fav.get("they_owe"):
        f_inner += "<div class=k>人家欠咱的</div>" + _ul(
            f"{p}（{a}）" for p, a in fav["they_owe"])
    blocks.append(_section("🤝 人情往来", f_inner))

    body = "".join(b for b in blocks if b)
    if not body:
        body = '<section class=card><p class=dim>还没有可展示的传家内容，去 config/ 里补充吧。</p></section>'

    return _PAGE.replace("{{name}}", name).replace("{{body}}", body)


def build_heritage(agent, out_path) -> str:
    """生成传家页到 out_path，返回文件路径。"""
    from pathlib import Path
    html = heritage_html(heritage_data(agent))
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return str(p)


_PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{name}} · 家珍册</title>
<style>
:root{--bg:#f6f1e7;--card:#fffdf8;--ink:#3a352c;--dim:#9a917f;--line:#e6ddc9;--accent:#a8703e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Noto Serif SC",serif;padding:24px}
.wrap{max-width:820px;margin:0 auto}
h1{font-size:28px;text-align:center;font-weight:700;margin:8px 0 2px}
.sub{text-align:center;color:var(--dim);margin-bottom:24px;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:16px 0;
      box-shadow:0 1px 0 #fff inset,0 2px 8px rgba(120,90,40,.05)}
h2{font-size:18px;margin:0 0 12px;color:var(--accent);border-bottom:1px dashed var(--line);padding-bottom:8px}
.k{font-size:13px;color:var(--dim);margin:12px 0 4px;font-weight:700}
ul{margin:6px 0;padding-left:20px}li{margin:4px 0}
.dim{color:var(--dim);font-size:13px;font-weight:400}
.genrow{display:flex;gap:10px;padding:4px 0;border-bottom:1px dotted var(--line)}
.genlab{min-width:64px;color:var(--accent);font-weight:700}
.story{margin:10px 0;padding:10px 12px;background:#fbf7ee;border-radius:10px;border-left:3px solid var(--accent)}
.stitle{font-weight:700;margin-bottom:4px}
.sbody{white-space:pre-wrap}
p{margin:6px 0}
footer{text-align:center;color:var(--dim);font-size:12px;margin:28px 0 8px}
</style></head>
<body><div class=wrap>
<h1>{{name}} · 家珍册</h1>
<div class=sub>这是分身替这个家守着的来路与念想 · 全部在本地</div>
{{body}}
<footer>digital-soul · 家珍册 · 一切都留在自己手里</footer>
</div></body></html>"""
