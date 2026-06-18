"""言传身教：把做人做事的道理、压箱底的手艺传给后人。
问"教我个做人的理""你那手艺怎么弄"，分身一条条说清；闲下来也会主动点拨一句。

配在 config/teachings.yaml（lessons 道理 / skills 手艺）。纯逻辑、可单测。
"""

from __future__ import annotations


def collect_lessons(config=None) -> list:
    """汇总人生道理：[{topic, lesson}, ...]。"""
    out = []
    for ln in ((config or {}).get("lessons") or []) if isinstance(config, dict) else []:
        if isinstance(ln, dict) and (ln.get("lesson") or ln.get("text")):
            out.append({"topic": str(ln.get("topic", "")).strip(),
                        "lesson": str(ln.get("lesson") or ln.get("text")).strip()})
        elif isinstance(ln, str) and ln.strip():
            out.append({"topic": "", "lesson": ln.strip()})
    return out


def collect_skills(config=None) -> list:
    """汇总手艺：[{name, steps, note}, ...]。"""
    out = []
    for s in ((config or {}).get("skills") or []) if isinstance(config, dict) else []:
        if isinstance(s, dict) and s.get("name"):
            steps = [str(x).strip() for x in (s.get("steps") or []) if str(x).strip()]
            out.append({"name": str(s["name"]).strip(), "steps": steps,
                        "note": str(s.get("note", "")).strip()})
    return out


def lesson_on(lessons, topic=None):
    """挑一条道理：有 topic 就挑最沾边的，否则给第一条。"""
    if not lessons:
        return None
    if topic:
        chars = set(str(topic))
        best, score = None, 0
        for ln in lessons:
            c = sum(1 for ch in chars if ch in (ln["topic"] + ln["lesson"]))
            if c > score:
                best, score = ln, c
        if best is not None:
            return best
    return lessons[0]


def teach_lesson(lesson) -> str:
    """把一条道理说给后人听。"""
    if not lesson:
        return ""
    head = f"说到{lesson['topic']}，" if lesson.get("topic") else ""
    return f"{head}我跟你讲：{lesson['lesson'].rstrip('。.')}。这话你记着。"


def find_skill(skills, query):
    """按手艺名在问话里找（名字长的优先）。"""
    if not skills or not query:
        return None
    q = str(query)
    for s in sorted(skills, key=lambda x: len(x["name"]), reverse=True):
        if s["name"] and s["name"] in q:
            return s
    return None


def teach_skill(skill) -> str:
    """手把手教一门手艺：分步骤 + 一句要诀。"""
    if not skill:
        return ""
    if not skill["steps"]:
        return f"{skill['name']}啊，我给你示范着来，光说讲不清。"
    steps = "；".join(f"{i + 1}）{st}" for i, st in enumerate(skill["steps"]))
    note = ("　要诀是：" + skill["note"]) if skill.get("note") else ""
    return f"{skill['name']}，照这几步来：{steps}。{note}".strip()


def lesson_titles(lessons) -> list:
    return [(ln["topic"] or ln["lesson"][:10]) for ln in (lessons or [])]


def skill_names(skills) -> list:
    return [s["name"] for s in (skills or []) if s.get("name")]
