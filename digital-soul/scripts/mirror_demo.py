#!/usr/bin/env python3
"""照镜子·表情自省演示：看分身怎么"用眼睛盯着自己的表情、一点点把它调到位"。

这是一条感知→动作的闭环：想要的表情 → 做出来 → 视觉读回真实神情 → 比差距 → 修正 → 再看。
没真摄像头时，用一面"模拟镜子"（做表情只有七八成力、还带点天生神态）来演示它会自己收敛。

  python scripts/mirror_demo.py            # 演示把"喜"调到位
  python scripts/mirror_demo.py 怒          # 换个情绪
  python scripts/mirror_demo.py 喜 0.55     # 再降点"力气"（damping），看它多调几次

真接视觉：把一个 perceive(动作)->{brow,eye,mouth_curve,mouth_open} 的函数传给 self_correct 即可，
（比如截图当前网页头像 / 摄像头拍脸 → 人脸关键点 → 这四个特征）。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul import expression_feedback as ef  # noqa: E402

_CN = {"brow": "眉", "eye": "眼", "mouth_curve": "嘴角", "mouth_open": "嘴"}


def main(argv=None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    emo = argv[0] if argv else "喜"
    damping = float(argv[1]) if len(argv) > 1 else 0.75

    target = ef.target_features(emo)
    print(f"想要的「{emo}」神情： " + "  ".join(f"{_CN[f]}{target[f]:+.2f}" for f in ef.features()))
    print("（镜子里做出来的只有约 %.0f%% 力，嘴角还天生有点下垂——看它怎么自己补上）\n" % (damping * 100))

    mirror = ef.make_mirror(damping=damping, bias={"mouth_curve": -0.2, "brow": -0.05})
    result = ef.self_correct(emo, mirror, gain=0.7, steps=12, tol=0.08)

    for s in result["trace"]:
        seen = s["observed"]
        bar = "  ".join(f"{_CN[f]}{seen[f]:+.2f}" for f in ef.features())
        print(f"  第{s['step']+1}次照镜子：{bar}   像「{s['looks_like']}」  差距 {s['score']:.3f}")

    print("\n" + ef.describe(emo, result))


if __name__ == "__main__":
    main()
