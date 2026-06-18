"""言传身教测试。可直接运行：python tests/test_teaching.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.teaching import (  # noqa: E402
    collect_lessons, collect_skills, find_skill, lesson_on, lesson_titles,
    skill_names, teach_lesson, teach_skill,
)

CFG = {
    "lessons": [
        {"topic": "诚信", "lesson": "答应人的事，砸锅卖铁也要办到。"},
        {"topic": "吃亏", "lesson": "吃亏是福，别总跟人争一时长短。"},
        "勤快点，懒不得。",
    ],
    "skills": [
        {"name": "包饺子", "steps": ["和面醒半小时", "调馅打水上劲", "包紧别露馅"],
         "note": "水开点三次凉水"},
        {"name": "钓鱼", "steps": []},
    ],
}


def test_collect():
    lessons = collect_lessons(CFG)
    assert len(lessons) == 3
    assert lessons[2] == {"topic": "", "lesson": "勤快点，懒不得。"}
    skills = collect_skills(CFG)
    assert skill_names(skills) == ["包饺子", "钓鱼"]


def test_lesson_on_topic():
    lessons = collect_lessons(CFG)
    ln = lesson_on(lessons, "吃亏")
    assert "吃亏是福" in ln["lesson"]
    assert lesson_on(lessons)["topic"] == "诚信"          # 无 topic 给第一条
    assert lesson_on([]) is None


def test_teach_lesson():
    s = teach_lesson({"topic": "诚信", "lesson": "答应的事要办到。"})
    assert "诚信" in s and "答应的事要办到" in s and "记着" in s
    assert teach_lesson(None) == ""


def test_find_and_teach_skill():
    skills = collect_skills(CFG)
    sk = find_skill(skills, "教我包饺子")
    assert sk["name"] == "包饺子"
    txt = teach_skill(sk)
    assert "1）和面" in txt and "水开点三次凉水" in txt
    # 没步骤的手艺，给个示范的说法
    assert "示范" in teach_skill(find_skill(skills, "钓鱼"))
    assert find_skill(skills, "没这手艺") is None


def test_titles():
    assert lesson_titles(collect_lessons(CFG))[0] == "诚信"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ teaching: all tests passed")
