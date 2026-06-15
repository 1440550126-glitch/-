"""技能注册表测试。可直接运行：python tests/test_skills.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.skills import SkillRegistry  # noqa: E402


class _Robot:
    def __init__(self):
        self.said = []
        self.moved = []

    def say(self, t):
        self.said.append(t)

    def move(self, d, m=1.0):
        self.moved.append((d, m))

    def look_at(self, t):
        pass

    def protect(self, t):
        pass


class _Agent:
    def __init__(self):
        self.robot = _Robot()


def test_builtin_skills_exist():
    r = SkillRegistry()
    assert "cook" in r.names()
    assert "clean" in r.names()


def test_cook_runs_and_speaks():
    r, a = SkillRegistry(), _Agent()
    msg = r.get("cook").run(a, dish="红烧肉")
    assert "红烧肉" in msg
    assert any("红烧肉" in s for s in a.robot.said)


def test_clean_moves_robot():
    r, a = SkillRegistry(), _Agent()
    r.get("clean").run(a, area="厨房")
    assert a.robot.moved  # 打扫会让机器人动起来


def test_permission_lookup():
    r = SkillRegistry()
    assert r.permission("cook") == "control_devices"
    assert r.permission("remind") == "chat"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ skills: all tests passed")
