"""情书：以 TA 本人的口吻，给老伴写一封走心的信。

开头唤只对TA用的昵称，中段忆我们怎么认识、这些年怎么走来，掏几句心窝子的话，
落款是你们之间的称呼。可在结婚纪念日、思念时读。优先用本地大模型润色，没有也能
用模板写出一封像样的。纯逻辑兜底、可单测。
"""

from __future__ import annotations

from .spouse import call_name

# 场景 → 开篇一句
_OCCASION = {
    "纪念日": "提笔这天，是我们的结婚纪念日。",
    "结婚纪念日": "提笔这天，是我们的结婚纪念日。",
    "生日": "今天是你生日，我想跟你说说话。",
    "思念": "夜深了，忽然很想跟你说说话。",
    "": "想给你写几个字，搁在心里好久了。",
}


def _heuristic_letter(profile, memories=None, occasion="") -> str:
    """不依赖大模型，也能凑出一封有温度的信。"""
    if not profile:
        return ""
    call = call_name(profile)
    body = []
    occ = _OCCASION.get(str(occasion).strip(), _OCCASION[""])
    if occ:
        body.append(occ)
    if profile.get("met"):
        body.append("还记得我们怎么认识的吗？" + profile["met"].rstrip("。.") + "。")
    if profile.get("story"):
        body.append("这些年一路走来——" + "；".join(profile["story"]) + "，桩桩件件我都记得。")
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if mems:
        body.append("我还总想起" + mems[0].rstrip("。.") + "。")
    for e in (profile.get("endearments") or [])[:2]:
        body.append(e)
    if profile.get("promises"):
        body.append("还有我们说好的——" + profile["promises"][0])
    body.append("往后的日子，照顾好自己，别太省、别熬夜。我一直都在，从没走远。")
    sign = profile.get("self_call") or "你的老伴"
    return f"{call}：\n　　{''.join(body)}\n\n　　　　　　　　　　{sign}"


def _llm_letter(profile, identity, memories, occasion, llm) -> str:
    """让本地大模型以 TA 的口吻写得更走心；失败则返回空，由上层兜底。"""
    if llm is None or not getattr(llm, "available", False):
        return ""
    name = (identity or {}).get("name", "我")
    call = call_name(profile)
    facts = []
    if profile.get("met"):
        facts.append("相识：" + profile["met"])
    if profile.get("story"):
        facts.append("一路走来：" + "；".join(profile["story"]))
    if profile.get("promises"):
        facts.append("约定：" + "；".join(profile["promises"]))
    if memories:
        facts.append("还记得：" + "；".join(str(m) for m in memories[:3]))
    system = (f"你是{name}，正在给挚爱的老伴「{call}」写一封情书。"
              "用第一人称、口语、真挚不肉麻，像一位相守多年的爱人。"
              "200 字以内，开头唤昵称，结尾落款，不要写日期。")
    user = "情书的由头：" + (occasion or "只是想你了") + "。可用的素材——" + "；".join(facts)
    try:
        text = llm.chat(system, user).strip()
        return text or ""
    except Exception:
        return ""


def compose_love_letter(profile, identity=None, memories=None, occasion="", llm=None) -> str:
    """写一封情书：先试大模型，再退回模板。没有老伴档案则空。"""
    if not profile:
        return ""
    return (_llm_letter(profile, identity, memories, occasion, llm)
            or _heuristic_letter(profile, memories, occasion))


def letter_html(text, profile=None) -> str:
    """把情书排成一张素净的信纸网页（自包含、可打印）。"""
    from html import escape
    call = escape(call_name(profile or {}))
    body = escape(text or "").replace("\n", "<br>")
    return _PAGE.replace("{{call}}", call).replace("{{body}}", body)


_PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>一封信 · 给{{call}}</title>
<style>
body{margin:0;background:#efe7d8;font:17px/2 "Noto Serif SC",serif;color:#41382c;padding:28px}
.paper{max-width:640px;margin:0 auto;background:#fffdf6;padding:40px 44px;border-radius:8px;
 box-shadow:0 10px 30px rgba(120,90,40,.15);
 background-image:repeating-linear-gradient(transparent,transparent 39px,#efe3cf 40px)}
.txt{white-space:normal}
.heart{text-align:center;color:#b76a52;margin-top:22px;font-size:20px}
</style></head><body>
<div class=paper><div class=txt>{{body}}</div><div class=heart>♡</div></div>
</body></html>"""
