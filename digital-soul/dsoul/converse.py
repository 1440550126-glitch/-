"""家人多人对谈：让数字宅里的两位（或更多）家人，各用各的口吻聊上几句。

这是"多人合一"与 Generative Agents 多智能体方向的交汇：每位用自己的性格 / 口头禅 / 记忆发言。
有本地大模型时用模型生成自然对话；没有也能用启发式拼出各有各味道的几轮。纯逻辑、可单测。
"""

from __future__ import annotations


def _valid(members) -> list:
    return [m for m in (members or []) if isinstance(m, dict) and m.get("name")]


def _opener(m) -> str:
    cps = m.get("catchphrases") or []
    return (str(cps[0]).rstrip("，。！？!? ") + "，") if cps else ""


def extract_topic(query, members) -> str:
    """从"让外公和外婆聊聊做饭"里抽出话题"做饭"；抽不出就用"家常"。"""
    t = str(query or "")
    for m in _valid(members):
        for s in (m.get("name"), m.get("relation")):
            if s:
                t = t.replace(str(s), "")
    for kw in ("让", "叫", "请", "和", "跟", "与", "俩", "仨", "们", "一起", "都",
               "聊聊", "聊", "说说", "说", "谈谈", "谈", "唠唠", "唠", "对谈", "对话", "一下"):
        t = t.replace(kw, "")
    return t.strip("，,。.、！!？? ") or "家常"


def _heuristic_dialogue(members, topic, rounds) -> list:
    turns, n = [], len(members)
    for r in range(max(1, rounds)):
        for i, m in enumerate(members):
            other = members[(i + 1) % n]["name"]
            op = _opener(m)
            if r == 0:
                mem = (m.get("memories") or [None])[0]
                text = (f"{op}说起{topic}，我就想起{str(mem).rstrip('。.')}。" if mem
                        else f"{op}聊{topic}啊，我有我的讲究。")
            else:
                text = f"{op}{other}说得在理，咱们一家人，怎么都好。"
            turns.append({"speaker": m["name"], "text": text})
    return turns


def _llm_dialogue(members, topic, llm, rounds) -> list:
    who = "、".join(
        f"{m['name']}（{m.get('relation', '家人')}，口头禅：{'/'.join(m.get('catchphrases') or []) or '无'}）"
        for m in members)
    system = "你擅长写温情的家常对话，每个人都说人话、有各自的性格。"
    prompt = (f"让这几位家人就「{topic}」自然地聊上 {rounds} 轮，每人每轮一句，"
              f"各用各的性格和口头禅，口语、简短、有来有往。\n家人：{who}\n"
              f"严格按「名字：内容」每行一句输出，别加旁白。")
    try:
        raw = llm.chat(system, prompt)
    except Exception:
        return []
    names = {m["name"] for m in members}
    turns = []
    for line in (raw or "").splitlines():
        line = line.strip()
        sep = "：" if "：" in line else (":" if ":" in line else None)
        if not sep:
            continue
        sp, text = line.split(sep, 1)
        sp, text = sp.strip().lstrip("-· "), text.strip()
        if sp in names and text:
            turns.append({"speaker": sp, "text": text})
    return turns


def family_dialogue(members, topic, llm=None, rounds: int = 2) -> list:
    """生成一段家人对谈：[{"speaker","text"}, …]。少于两人则空。"""
    members = _valid(members)
    if len(members) < 2:
        return []
    topic = (topic or "家常").strip() or "家常"
    if llm is not None and getattr(llm, "available", False):
        turns = _llm_dialogue(members, topic, llm, rounds)
        if turns:
            return turns
    return _heuristic_dialogue(members, topic, rounds)
