"""跨天记挂测试。可直接运行：python tests/test_follow_through.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.follow_through import find_thread, followup_line  # noqa: E402


def test_find_thread_types():
    assert find_thread("我下周要去面试")[0] == "大事"
    assert find_thread("这两天腰一直疼")[0] == "不适"
    assert find_thread("我打算把老屋翻修一下")[0] == "打算"
    assert find_thread("我有点担心孩子的成绩")[0] == "难处"


def test_find_thread_skips_questions_and_chitchat():
    assert find_thread("你吃饭了吗") is None
    assert find_thread("今天天气真好") is None


def test_find_thread_gist_trimmed():
    kind, gist = find_thread("我下周要去面试，那家公司挺大的，有点紧张")
    assert kind == "大事" and len(gist) <= 16 and "面试" in gist


def test_followup_line():
    assert "顺利吗" in followup_line("大事", "要去面试")
    assert "好些了没" in followup_line("不适", "腰疼")
    assert "后来咋样" in followup_line("打算", "翻修老屋")
    assert followup_line("大事", "") == ""               # 没摘要就不问


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ follow_through: all tests passed")
