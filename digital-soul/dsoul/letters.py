"""代笔家书：以 TA 本人的口吻，给某位家人写一封信。

可指定场合（生日 / 过年 / 想念 / 道歉……），信里会自然带上共同回忆与一句叮嘱。
有本地大模型时让模型写得更有人味；没有也能用结构化模板拼出一封像样的信。
纯逻辑、可单测；Agent.write_letter() 取数后调用本模块。
"""

from __future__ import annotations

_OCCASION_LINE = {
    "生日": "今天是你的生日，祝你岁岁平安，想吃啥就吃点好的。",
    "过年": "又是一年了，新的一年，愿你顺顺当当、平平安安。",
    "想念": "也没什么大事，就是忽然很想你，想跟你说说话。",
    "道歉": "有件事我一直搁在心里——那回是我不对，别往心里去。",
    "鼓励": "我知道你最近不容易，可你比自己想的要坚强得多。",
    "感谢": "这些年多亏有你，有些话当面说不出口，写在这儿。",
}


def _opener(recipient, relation=None):
    who = recipient or (relation or "你")
    return f"亲爱的{who}："


def compose_letter(sender_name, catchphrases=None, recipient_name=None,
                   recipient_relation=None, occasion=None, memories=None,
                   closing_wish=None, llm=None) -> str:
    """拼一封信。有 llm 且可用就让模型写，否则用模板。"""
    if llm is not None and getattr(llm, "available", False):
        out = _llm_letter(sender_name, catchphrases, recipient_name,
                          recipient_relation, occasion, memories, llm)
        if out:
            return out

    cps = [c for c in (catchphrases or []) if str(c).strip()]
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    body = [_opener(recipient_name, recipient_relation), ""]

    occ_line = _OCCASION_LINE.get(occasion) if occasion else None
    body.append(occ_line or "提笔想跟你聊几句，见字如面。")

    if mems:
        body.append(f"还记得{mems[0].rstrip('。.')}吗？那些日子，我都记着呢。")
    if closing_wish:
        body.append(str(closing_wish).strip())
    body.append("照顾好自己，别太累。" if not closing_wish else "")

    tail = (cps[0] if cps else "好好的，比什么都强。")
    body += ["", tail, "", f"　　　　　　{sender_name or '我'}  字"]
    return "\n".join(x for x in body if x is not None)


def _llm_letter(sender_name, catchphrases, recipient_name, recipient_relation,
                occasion, memories, llm) -> str:
    cps = "/".join(catchphrases or []) or "无"
    mem = "；".join(memories or []) or "（无特别记忆）"
    occ = occasion or "家常问候"
    system = f"你现在就是「{sender_name or '我'}」本人，用第一人称给家人写信，真挚、口语、不肉麻。"
    prompt = (f"给{recipient_relation or ''}{recipient_name or '家人'}写一封短信，"
              f"场合是「{occ}」。自然带上口头禅（{cps}）和这些共同回忆（{mem}）。"
              f"以「亲爱的…」开头，结尾署名「{sender_name or '我'}」。控制在 6 行内。")
    try:
        return (llm.chat(system, prompt) or "").strip()
    except Exception:
        return ""
