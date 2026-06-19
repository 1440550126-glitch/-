"""急救信息卡：把救命的要紧信息汇成一张卡——姓名、慢病、过敏、在吃的药、血型、
紧急联系人。打印出来随身带，万一出事，旁人和医生一眼就知道该怎么办、找谁。

从 identity/health/medications/contacts 汇集，纯逻辑生成卡片，可单测。
"""

from __future__ import annotations

from html import escape


def card_data(agent) -> dict:
    """汇集急救卡要紧信息；每块各自降级。"""
    def _try(fn, default):
        try:
            return fn()
        except Exception:
            return default

    idy = getattr(agent, "identity", {}) or {}
    health = getattr(agent, "health", {}) or {}

    def _conds():
        from .health_history import collect_conditions
        return [f"{c['condition']}" for c in collect_conditions(health)]

    def _allergies():
        from .health_history import allergies
        # 只取本人的过敏（或全部）；卡片上是给本人用的
        return [a["to"] for a in allergies(health)]

    def _meds():
        m = getattr(agent, "medications", None)
        return [x["name"] for x in m.meds] if m is not None else []

    def _contacts():
        c = getattr(agent, "contacts", None)
        if c is None:
            return []
        return [f"{x['relation'] or x['name']} {x['phone']}".strip()
                for x in c.emergency_contacts() if x.get("phone")]

    return {
        "name": idy.get("name", "（未填姓名）"),
        "blood": health.get("blood_type") or idy.get("blood_type") or "",
        "conditions": _try(_conds, []),
        "allergies": _try(_allergies, []),
        "meds": _try(_meds, []),
        "contacts": _try(_contacts, []),
    }


def card_text(data) -> str:
    """纯文本急救卡（可读、可贴冰箱）。"""
    d = data or {}
    lines = [f"【急救信息卡】 {d.get('name', '')}"]
    if d.get("blood"):
        lines.append(f"血型：{d['blood']}")
    if d.get("conditions"):
        lines.append("慢性病：" + "、".join(d["conditions"]))
    if d.get("allergies"):
        lines.append("过敏：" + "、".join(d["allergies"]))
    if d.get("meds"):
        lines.append("在服药物：" + "、".join(d["meds"]))
    if d.get("contacts"):
        lines.append("紧急联系人：" + "；".join(d["contacts"]))
    lines.append("如遇紧急情况，请拨打 120，并按上方联系人通知家属。")
    return "\n".join(lines)


def card_html(data) -> str:
    d = data or {}
    def _row(label, val):
        return f'<tr><td class=k>{escape(label)}</td><td>{escape(val)}</td></tr>' if val else ""
    rows = "".join([
        _row("血型", d.get("blood", "")),
        _row("慢性病", "、".join(d.get("conditions", []))),
        _row("过敏", "、".join(d.get("allergies", []))),
        _row("在服药物", "、".join(d.get("meds", []))),
        _row("紧急联系人", "；".join(d.get("contacts", []))),
    ])
    return _PAGE.replace("{{name}}", escape(d.get("name", ""))).replace("{{rows}}", rows)


def build_card(agent, out_path) -> str:
    from pathlib import Path
    html = card_html(card_data(agent))
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return str(p)


_PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>急救信息卡</title>
<style>
body{font:15px/1.7 system-ui,sans-serif;background:#fff;color:#222;margin:0;padding:16px}
.card{max-width:420px;margin:0 auto;border:2px solid #c0392b;border-radius:12px;padding:16px 18px}
h1{color:#c0392b;font-size:19px;margin:0 0 4px}.sub{color:#888;font-size:12px;margin-bottom:10px}
table{width:100%;border-collapse:collapse}td{padding:6px 4px;border-bottom:1px dashed #eee;vertical-align:top}
.k{color:#c0392b;font-weight:700;width:84px;white-space:nowrap}
.foot{margin-top:12px;color:#c0392b;font-weight:700;text-align:center}
</style></head><body>
<div class=card><h1>🆘 急救信息卡 · {{name}}</h1>
<div class=sub>随身携带 · 万一出事，请按此联系家人、告知医生</div>
<table>{{rows}}</table>
<div class=foot>紧急请拨 120</div></div>
</body></html>"""
