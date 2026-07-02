"""授权系统测试：听谁的、不听谁的、谁能让我做什么。

可直接运行：python tests/test_authority.py
也可用 pytest 跑。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.authority import Authority  # noqa: E402

CONFIG = {
    "trust_levels": {"owner": 100, "family": 80, "friend": 50, "stranger": 0, "blocked": -1},
    "permissions": {
        "owner": ["*"],
        "family": ["chat", "protect", "move"],
        "friend": ["chat"],
        "stranger": ["chat_limited"],
        "blocked": [],
    },
    "people": [
        {"name": "张明", "relation": "本人", "trust": "owner", "obey": True},
        {"name": "小婷", "relation": "老婆", "trust": "family", "obey": True,
         "guard": True, "feelings": "最爱的人"},
        {"name": "老钱", "relation": "前同事", "trust": "blocked", "obey": False},
    ],
}


def test_owner_can_do_anything():
    a = Authority(CONFIG)
    ok, _, _ = a.can("张明", "shutdown")
    assert ok


def test_family_can_protect_but_not_shutdown():
    a = Authority(CONFIG)
    assert a.can("小婷", "protect")[0] is True
    assert a.can("小婷", "shutdown")[0] is False


def test_stranger_cannot_shutdown():
    a = Authority(CONFIG)
    ok, who, _ = a.can("路人甲", "shutdown")
    assert ok is False
    assert who["known"] is False


def test_blocked_is_never_obeyed():
    a = Authority(CONFIG)
    ok, who, reason = a.can("老钱", "chat")
    assert ok is False
    assert who["obey"] is False
    assert "不会听" in reason


def test_guard_list():
    a = Authority(CONFIG)
    assert "小婷" in a.guarded_people()


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("PASS", _name)
    print("✅ authority: all tests passed")
