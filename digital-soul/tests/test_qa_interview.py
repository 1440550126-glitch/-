"""生平采访测试。可直接运行：python tests/test_qa_interview.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.qa_interview import (INTERVIEW, all_questions,  # noqa: E402
                                answer_to_memory, next_question, progress)


def test_question_bank_nonempty_and_flat():
    flat = all_questions()
    assert len(flat) >= 15
    assert all(isinstance(s, str) and isinstance(q, str) for s, q in flat)
    assert {s for s, _ in flat} == {stage for stage, _ in INTERVIEW}


def test_next_question_advances():
    first = next_question([])
    assert first == all_questions()[0]
    asked = [q for _, q in all_questions()]
    assert next_question(asked) is None              # 都问完
    one_left = asked[:-1]
    assert next_question(one_left) == all_questions()[-1]


def test_progress():
    assert progress([]) == 0.0
    assert progress([q for _, q in all_questions()]) == 1.0
    half = [q for _, q in all_questions()][:len(all_questions()) // 2]
    assert 0 < progress(half) < 1


def test_answer_to_memory_extracts_year():
    rec = answer_to_memory("我1990年出生在成都")
    assert rec["text"].startswith("我1990") and rec["when"] == "1990"
    assert answer_to_memory("   ") is None


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ qa_interview: all tests passed")
