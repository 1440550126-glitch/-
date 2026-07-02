"""居家安全测试。可直接运行：python tests/test_safety_check.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.safety_check import (  # noqa: E402
    checklist, evening_prompt, is_safety_query, reassure,
)


def test_checklist_default_and_custom():
    assert "门锁好了吗" in checklist()
    assert checklist({"items": ["阳台门关了吗"]}) == ["阳台门关了吗"]
    assert checklist({"items": []}) == checklist()        # 空配置回落默认


def test_evening_prompt():
    p = evening_prompt(["门锁了吗", "燃气关了吗"])
    assert "门锁了吗" in p and "燃气关了吗" in p and "安心睡" in p


def test_is_safety_query():
    assert is_safety_query("睡前检查一下")
    assert is_safety_query("门窗都关了吗")
    assert not is_safety_query("今天吃什么")


def test_reassure():
    assert "安心睡" in reassure()


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ safety_check: all tests passed")
