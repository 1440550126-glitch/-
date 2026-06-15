"""量子纠缠式记忆测试。可直接运行：python tests/test_entangle.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.entangle import entangled_with, entanglement, spreading_activation  # noqa: E402

NAMES = ["小婷"]
A = {"id": "a", "text": "我和小婷在篮球场认识", "emotion": "深情"}
B = {"id": "b", "text": "小婷喜欢看我打篮球", "emotion": "深情"}
C = {"id": "c", "text": "今天股票跌了心情一般", "emotion": "平静"}


def test_entanglement_correlated_vs_unrelated():
    assert entanglement(A, B, NAMES) > entanglement(A, C, NAMES)   # 共享小婷/篮球/情感
    assert entanglement(A, C, NAMES) < 0.2                          # 几乎不相关


def test_emotion_bonus():
    base = {"id": "x", "text": "我和小婷在篮球场认识", "emotion": "平静"}
    # 同样的文本，强情感一致时纠缠更强
    assert entanglement(A, B, NAMES) > entanglement(base, {**B, "emotion": "平静"}, NAMES)


def test_entangled_with_ranks():
    top = entangled_with(A, [A, B, C], NAMES, k=2)
    assert top and top[0][1]["id"] == "b"


def test_spreading_activation_excludes_seed():
    sa = spreading_activation([A], [A, B, C], names=NAMES, k=3)
    ids = [it["id"] for _, it in sa]
    assert "b" in ids and "a" not in ids                           # 牵动 B，不含种子 A


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ entangle: all tests passed")
