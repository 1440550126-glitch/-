"""表情自省（视觉闭环自我修正）测试。可直接运行：python tests/test_expression_feedback.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.expression_feedback import (  # noqa: E402
    correct, describe, features, make_mirror, mismatch, read_expression,
    self_correct, target_features,
)


def test_targets_cover_seven_emotions():
    for e in ("喜", "乐", "哀", "惧", "怒", "爱", "欲", "中"):
        t = target_features(e)
        assert set(t.keys()) == set(features())
    # 喜应当嘴角上扬、哀应当下撇
    assert target_features("喜")["mouth_curve"] > 0.5
    assert target_features("哀")["mouth_curve"] < 0
    assert target_features("乱七八糟") == target_features("中")   # 认不出按平和


def test_mismatch_zero_when_equal():
    t = target_features("喜")
    m = mismatch(t, dict(t))
    assert m["score"] == 0.0
    # 差得越多分越高
    m2 = mismatch(t, {"brow": 0, "eye": 0, "mouth_curve": 0, "mouth_open": 0})
    assert m2["score"] > 0.2


def test_correct_moves_toward_target():
    t = target_features("喜")
    obs = {"brow": 0, "eye": 0, "mouth_curve": 0, "mouth_open": 0}
    act0 = {f: 0.0 for f in features()}
    act1 = correct(act0, t, obs, gain=0.6)
    # 嘴角目标为正，没做到 → 动作往正向加
    assert act1["mouth_curve"] > act0["mouth_curve"]


def test_self_correct_converges_against_biased_face():
    # 一张'只有七成力、嘴角天生下垂'的脸，照镜子能把"喜"调到位
    mirror = make_mirror(damping=0.7, bias={"mouth_curve": -0.2})
    r = self_correct("喜", mirror, gain=0.7, steps=12, tol=0.08)
    assert r["ok"] is True
    assert r["final_score"] <= 0.08
    assert r["steps"] >= 2                       # 确实是"逐步"修正，不是一下到位
    # 看到的嘴角一步步往上走（自我修正的轨迹）
    seen = [s["observed"]["mouth_curve"] for s in r["trace"]]
    assert seen[-1] > seen[0]


def test_self_correct_one_step_not_enough():
    mirror = make_mirror(damping=0.7, bias={"mouth_curve": -0.3})
    r = self_correct("乐", mirror, gain=0.5, steps=1)
    assert r["ok"] is False and r["steps"] == 1


def test_read_expression_nearest():
    assert read_expression(target_features("怒")) == "怒"
    assert read_expression(target_features("喜")) == "喜"
    assert read_expression({"brow": 0, "eye": 0, "mouth_curve": 0, "mouth_open": 0}) == "中"


def test_describe_ok_and_not_ok():
    mirror = make_mirror(damping=0.7, bias={"mouth_curve": -0.2})
    ok = self_correct("喜", mirror, gain=0.7, steps=12)
    s = describe("喜", ok)
    assert "到位" in s and "镜子" in s
    bad = self_correct("乐", make_mirror(damping=0.5, bias={"mouth_curve": -0.4}), gain=0.4, steps=1)
    s2 = describe("乐", bad)
    assert "还差点意思" in s2 and ("嘴" in s2 or "眉" in s2 or "眼" in s2)


def test_determinism_no_noise():
    m1 = make_mirror(damping=0.7, bias={"brow": -0.1})
    m2 = make_mirror(damping=0.7, bias={"brow": -0.1})
    r1 = self_correct("惧", m1, steps=6)
    r2 = self_correct("惧", m2, steps=6)
    assert r1["final_score"] == r2["final_score"] and r1["steps"] == r2["steps"]


def test_config_override_targets():
    cfg = {"expression_targets": {"喜": {"mouth_curve": 0.3}}}
    assert target_features("喜", cfg)["mouth_curve"] == 0.3


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ expression_feedback: all tests passed")
