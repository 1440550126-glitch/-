"""宽慰忧虑测试。可直接运行：python tests/test_worries.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.worries import detect_theme, senses_worry, soothe_worry  # noqa: E402


def test_senses_worry():
    assert senses_worry("我有点担心钱不够")
    assert senses_worry("万一查出毛病怎么办")
    assert not senses_worry("今天挺开心")


def test_detect_theme():
    assert detect_theme("房贷压力好大") == "钱"
    assert detect_theme("怕体检查出问题") == "健康"
    assert detect_theme("项目黄了会不会被裁") == "工作"
    assert detect_theme("就是心里发慌") is None


def test_soothe_tailored():
    s = soothe_worry("我担心还不上房贷", name="小明")
    assert s.startswith("小明，") and "不踏实" in s and "办法总比难处多" in s
    h = soothe_worry("怕生病")
    assert "早查早安心" in h


def test_soothe_generic():
    s = soothe_worry("心里就是慌")
    assert "天塌不下来" in s and "陪着你" in s
    for bad in ("死", "忌日", "不在了"):
        assert bad not in s


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ worries: all tests passed")
