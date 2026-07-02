"""可校准预测测试。可直接运行：python tests/test_predict.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.predict import Calibration, predict  # noqa: E402


def _ts(h):
    return datetime(2024, 1, 1, h, 0).timestamp()


def test_predict_returns_signal_with_confidence():
    entries = [{"ts": _ts(9), "utterance": "早上又要赶去加班"},
               {"ts": _ts(9), "utterance": "唉又加班"},
               {"ts": _ts(9), "utterance": "加班好累"}]
    p = predict(entries, now=datetime(2024, 1, 1, 9, 30))
    assert p and "加班" in p["label"] and 0 < p["confidence"] <= 0.97
    assert p["source"] == "时段习惯"


def test_calibration_learns_from_feedback():
    cb = Calibration(tempfile.mktemp(suffix=".json"))
    f0 = cb.factor("时段习惯")
    assert abs(f0 - 1.0) < 1e-9                              # 起步中性
    for _ in range(4):
        cb.feedback("时段习惯", True)                        # 屡猜对
    assert cb.factor("时段习惯") > f0                        # 该信号更可信
    cb2 = Calibration(tempfile.mktemp(suffix=".json"))
    for _ in range(4):
        cb2.feedback("时段习惯", False)                      # 屡猜错
    assert cb2.factor("时段习惯") < 1.0                      # 该信号被打折


def test_calibration_changes_prediction_confidence():
    entries = [{"ts": _ts(9), "utterance": "早上加班"} for _ in range(3)]
    base = predict(entries, now=datetime(2024, 1, 1, 9, 30))
    cb = Calibration(tempfile.mktemp(suffix=".json"))
    for _ in range(5):
        cb.feedback("时段习惯", False)
    worse = predict(entries, now=datetime(2024, 1, 1, 9, 30), calib=cb)
    assert worse["confidence"] < base["confidence"]         # 校准后置信度下降


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ predict: all tests passed")
