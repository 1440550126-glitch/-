"""面部舵机驱动测试。可直接运行：python tests/test_face_motors.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul import expression_feedback as ef  # noqa: E402
from dsoul.face_motors import (  # noqa: E402
    DEFAULT_RIG, FaceRig, at_limit, channels, drive, express_on_face,
    feature_to_pulses, make_recorder, make_sim_face, neutral_pulses,
    pulses_to_features, robot_sender,
)


def test_channels_and_neutral():
    ch = channels()
    for c in ("brow_l", "eyelid_r", "mouth_l", "jaw"):
        assert c in ch
    n = neutral_pulses()
    assert n["brow_l"] == 1500 and n["jaw"] == 1200


def test_feature_to_pulses_direction():
    # 嘴角上扬 → 嘴角舵机脉宽 > 中位；嘴角下撇 → < 中位
    up = feature_to_pulses({"mouth_curve": 0.8})
    down = feature_to_pulses({"mouth_curve": -0.8})
    assert up["mouth_l"] > 1500 > down["mouth_l"]
    # 张嘴 → jaw 抬高
    assert feature_to_pulses({"mouth_open": 1.0})["jaw"] > feature_to_pulses({"mouth_open": 0.0})["jaw"]


def test_safety_clamp():
    big = feature_to_pulses({"mouth_curve": 9.0, "brow": -9.0})
    for c, (_f, _n, _s, _d, lo, hi) in DEFAULT_RIG.items():
        assert lo <= big[c] <= hi                     # 绝不超出安全限位
    assert "mouth_l" in at_limit(big)


def test_pulses_features_roundtrip():
    target = ef.target_features("哀")
    back = pulses_to_features(feature_to_pulses(target))
    for f in ("brow", "eye", "mouth_curve", "mouth_open"):
        assert abs(back[f] - target[f]) < 0.05        # 映射可逆（未到限位时）


def test_drive_uses_sender_and_is_graceful():
    sender, log = make_recorder()
    p = drive(ef.target_features("喜"), sender)
    assert log and log[-1] == p

    def boom(_):
        raise RuntimeError("hw fail")
    # sender 出错不该抛
    assert drive(ef.target_features("喜"), boom) == p


def test_robot_sender_graceful():
    assert robot_sender(None) is None
    assert robot_sender(object()) is None             # 没 face 方法

    class Bot:
        def __init__(self):
            self.got = None

        def face(self, channels):
            self.got = channels
    b = Bot()
    s = robot_sender(b)
    s({"jaw": 1300})
    assert b.got == {"jaw": 1300}


def test_facerig_smooth_settle():
    rig = FaceRig(ease=0.5)
    sender, log = make_recorder()
    n, cur = rig.goto(ef.target_features("乐"), sender, max_steps=20)
    assert n >= 2 and rig.settled()                   # 平滑过渡、最终到位
    assert len(log) == n                              # 每步都发了


def test_open_loop_express():
    sender, log = make_recorder()
    r = express_on_face("喜", sender)                  # 没摄像头 → 开环
    assert r["closed_loop"] is False and log
    assert r["pulses"]["mouth_l"] > 1500


def test_closed_loop_self_corrects_on_motors():
    # 模拟舵机+摄像头：脸天生嘴角下垂、做表情只有八成力，闭环把'喜'调到位
    sender, camera = make_sim_face(damping=0.8, bias={"mouth_curve": -0.2})
    r = express_on_face("喜", sender, perceive=camera, gain=0.8, steps=15, tol=0.08)
    assert r["closed_loop"] is True and r["ok"] is True
    # 为补偿下垂的脸，嘴角舵机被"多使劲"（超过开环目标脉宽）
    open_loop = feature_to_pulses(ef.target_features("喜"))["mouth_l"]
    assert r["pulses"]["mouth_l"] >= open_loop


def test_closed_loop_reports_limit_when_unreachable():
    # 偏置极大、力气又小：够不到目标，应当 ok=False 且有舵机顶到限位
    sender, camera = make_sim_face(damping=0.5, bias={"mouth_curve": -1.0})
    r = express_on_face("乐", sender, perceive=camera, gain=0.6, steps=10, tol=0.05)
    assert r["ok"] is False
    assert r["at_limit"]                              # 顶到机械极限、调不动了


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ face_motors: all tests passed")
