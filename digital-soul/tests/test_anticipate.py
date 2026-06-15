"""情景预测测试。可直接运行：python tests/test_anticipate.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.anticipate import _bucket, predict  # noqa: E402


def _ts(h):
    return datetime(2024, 1, 1, h, 0).timestamp()


def test_bucket_boundaries():
    assert _bucket(7) == "早上" and _bucket(13) == "中午"
    assert _bucket(20) == "晚上" and _bucket(3) == "深夜"


def test_predict_recurring_topic_for_time():
    entries = [{"ts": _ts(9), "utterance": "今天又要加班好累"},
               {"ts": _ts(9), "utterance": "唉还是加班"},
               {"ts": _ts(9), "utterance": "加班加到头秃"},
               {"ts": _ts(20), "utterance": "晚上看个电影放松"}]
    out = predict(entries, now=datetime(2024, 1, 1, 9, 30))
    assert "加班" in out and "早上" in out                  # 早上常念叨加班
    # 晚上只有一条，达不到阈值 → 不硬预测
    assert predict(entries, now=datetime(2024, 1, 1, 20, 30)) == ""


def test_no_data_no_prediction():
    assert predict([], now=datetime(2024, 1, 1, 9, 0)) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ anticipate: all tests passed")
