#!/usr/bin/env python3
"""面部舵机演示：把"表情"变成舵机脉宽，开环摆一个、再走视觉闭环边看边调。

  python scripts/face_demo.py            # 演示"喜"
  python scripts/face_demo.py 哀

没硬件时用一面"模拟舵机+摄像头"（脸做表情只有八成力、嘴角天生下垂）跑整条链路；
真接硬件：实现 RobotInterface.face(channels)（PCA9685/串口/ROS2 /soul/face），
把 face_motors.robot_sender(robot) 当 sender 传进去即可。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul import expression_feedback as ef  # noqa: E402
from dsoul import face_motors as fm  # noqa: E402


def _line(pulses):
    return "  ".join(f"{c}={pulses[c]}" for c in
                     ("brow_l", "eyelid_l", "mouth_l", "mouth_r", "jaw") if c in pulses)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    emo = argv[0] if argv else "喜"

    print(f"=== 开环：直接把「{emo}」摆到舵机上 ===")
    sender, log = fm.make_recorder()
    fm.express_on_face(emo, sender, perceive=None)
    print("  舵机脉宽:", _line(log[-1]))

    print(f"\n=== 平滑过渡：从放松脸缓动到「{emo}」 ===")
    rig = fm.FaceRig(ease=0.5)
    s2, log2 = fm.make_recorder()
    n, _ = rig.goto(ef.target_features(emo), s2, max_steps=10)
    for i, p in enumerate(log2):
        print(f"  第{i+1}步: {_line(p)}")

    print(f"\n=== 视觉闭环：边看自己边把「{emo}」调到位（脸天生嘴角下垂、力气只有八成）===")
    sim_send, camera = fm.make_sim_face(damping=0.8, bias={"mouth_curve": -0.2})
    r = fm.express_on_face(emo, sim_send, perceive=camera, gain=0.8, steps=12)
    for s in r["trace"]:
        seen = s["observed"]
        bar = "  ".join(f"{k}{seen[k]:+.2f}" for k in ("brow", "mouth_curve"))
        print(f"  第{s['step']+1}次照镜子: 看着{bar}  像「{s['looks_like']}」 差距 {s['score']:.3f}"
              f"  →舵机 mouth_l={r['pulses']['mouth_l'] if s is r['trace'][-1] else '...'}")
    print("  最终舵机脉宽:", _line(r["pulses"]))
    if r.get("at_limit"):
        print("  ⚠️ 顶到限位的舵机:", "、".join(r["at_limit"]))
    print("\n" + ef.describe(emo, r))


if __name__ == "__main__":
    main()
