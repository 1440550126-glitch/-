"""知识沉淀：睡前/巩固时，把当天对话里"聊到的知识"自动沉进自生长知识库。

分身一天里答过的那些有知识含量的话（讲了川菜、节气、麻将术语、戏曲行当……），
不该聊完就忘——这一块从对话日记里挑出这些"概念：解释"，自动写成 Obsidian 笔记、
连进图谱。区别于"记忆巩固"(consolidate 把私人经历存进 RAG)：那个记"和谁发生了什么"，
这个攒"世界是什么样"。纯逻辑、可单测（喂一批日记条目就行）。
"""

from __future__ import annotations

import re

# 这些路由的回复是"概念/知识"，值得沉进知识库（文化/常识/百科类，挑稳定能立词条的）
KNOWLEDGE_ROUTES = {
    "cuisines", "specialty", "festive_foods", "liquor_culture", "scholar_tools",
    "mahjong", "board_games", "opera", "opera_roles", "quyi", "classic_films",
    "old_objects", "old_trades", "folk_customs", "festival_lore", "idiom_story",
    "solar_terms", "astronomy", "dynasties", "historical_figures", "inventions",
    "landmarks", "zodiac_lore", "myths", "animal_facts", "colors_cn", "calligraphy",
    "instruments", "ganzhi", "surnames", "weather_terms", "food_label", "naming",
    "medical_exams", "vaccines", "acupoints",
}

# 标题里常见的、可以削掉的后缀（让"饺子的讲究"→"饺子"）
_TITLE_TAIL = re.compile(r"(的讲究|的来由|的寓意|怎么下|怎么用|怎么看|怎么养|怎么走|是什么|啥意思|简介)$")
# 一看就不是知识的开头（问候/安抚/记忆兜底）
_BAD_HEAD = ("哈哈", "别慌", "别急", "我在", "我记得", "听你", "你说", "好嘞", "好的", "嗯")


def split_concept(reply: str):
    """从一句"概念：解释"的回复里拆出 (标题, 正文)。拆不出（不是词条形）返回 None。"""
    reply = str(reply or "").strip()
    if not reply or reply.startswith(_BAD_HEAD):
        return None
    m = re.match(r"^\s*([^：:（(]{1,20})[：:（(]", reply)
    if not m:
        return None
    title = m.group(1).strip().strip("「」『』\"《》 ")
    title = _TITLE_TAIL.sub("", title).strip()
    if len(title) < 2 or re.search(r"[，。！？、,.!?\n]", title):
        return None
    return title, reply


def candidates(entries, routes=None) -> list:
    """从日记条目里挑出该沉淀的知识候选。entries：[{utterance,reply,executed,speaker},...]"""
    routes = routes if routes is not None else KNOWLEDGE_ROUTES
    out, seen = [], set()
    for e in entries or []:
        if (e.get("executed") or e.get("route")) not in routes:
            continue
        cb = split_concept(e.get("reply", ""))
        if not cb:
            continue
        title, body = cb
        if title in seen:
            continue
        seen.add(title)
        out.append({"title": title, "body": body,
                    "tag": (e.get("executed") or e.get("route")),
                    "speaker": e.get("speaker") or "对话"})
    return out


def sediment(vault, entries, *, now=None, daily=True, routes=None) -> dict:
    """把一批日记条目里的知识沉进 vault：没有的新建、有的补充新内容（不重复）。返回报告。"""
    cands = candidates(entries, routes)
    created, appended = [], []
    for c in cands:
        if not vault.has(c["title"]):
            vault.grow(c["title"], c["body"], tags=[c["tag"]],
                       source=f"沉淀·{c['speaker']}", now=now)
            created.append(c["title"])
        else:
            cur = vault.note(c["title"]) or {}
            if c["body"].strip() and c["body"].strip() not in (cur.get("body") or ""):
                vault.grow(c["title"], c["body"], tags=[c["tag"]], now=now)   # 追加补记
                appended.append(c["title"])
            # 否则：已知，跳过，不churn
    touched = created + appended
    if daily and touched:
        vault.daily_note("今天沉淀了：" + "、".join(touched), links=touched, now=now)
    return {"created": created, "appended": appended,
            "candidates": len(cands), "touched": touched}
