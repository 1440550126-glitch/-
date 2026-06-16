#!/usr/bin/env python3
"""缅怀演示：一个「外公」的数字分身，如何陪伴想念他的孙女。

把前面所有能力串起来——本人口吻、共同回忆、纪念日主动提起、思念时温柔抚慰——
全在临时目录里跑，不动你的真实数据。用法：python scripts/memorial_demo.py

⚠️ 它是一面承载记忆的镜子，帮在世的人好好怀念与告别，不是、也不该替代那个人本身。
"""

import datetime
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402

IDENTITY = """name: "外公"
personality:
  speaking_style: "慢条斯理，爱讲老理儿，最疼孩子"
  traits: ["温厚", "念旧", "嘴上唠叨心里软"]
  catchphrases: ["乖乖", "莫慌", "听外公的"]
  particles: ["嘛", "撒"]
"""
RELATIONS = """trust_levels: {owner: 100, family: 80, stranger: 0}
permissions:
  owner: ["*"]
  family: ["protect", "control_devices", "control_agents"]
  stranger: []
people:
  - {name: "外公", relation: "本人", trust: "owner"}
  - {name: "小婷", relation: "孙女", trust: "family", guard: true}
"""
LIFE = """我和小婷在院子里种了一棵桂花树，每年秋天，满院子都是甜香。
小婷小时候我教她骑自行车，她摔了好几回也不哭，倔得很，随我。
我最拿手的是红烧肉，小婷最爱吃，每次都要添两碗饭。
"""


def _base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-memorial-"))
    (tmp / "config").mkdir(parents=True)
    (tmp / "config" / "identity.yaml").write_text(IDENTITY, encoding="utf-8")
    (tmp / "config" / "relationships.yaml").write_text(RELATIONS, encoding="utf-8")
    today = datetime.date.today().strftime("%m-%d")
    (tmp / "config" / "memorial.yaml").write_text(f'dates:\n  外公的生日: "{today}"\n', encoding="utf-8")
    src = tmp / "data" / "memories" / "sources"
    src.mkdir(parents=True)
    (src / "life.md").write_text(LIFE, encoding="utf-8")
    (tmp / "data" / "faces").mkdir(parents=True)
    return tmp


def main() -> None:
    base = _base()
    try:
        a = build_agent(base_dir=base)
        print("🕯️  「外公」的数字分身（基于他生前的话与你们的回忆，临时目录运行）\n")

        print("① 小婷走近 —— 外公主动打招呼（今天恰是他生日）")
        print("   外公:", a.greet("小婷"), "\n")

        for words in ["外公，我好想你。", "你还记得我们种的那棵桂花树吗？", "你最拿手的菜是什么呀？"]:
            print(f"   小婷: {words}")
            print(f"   外公: {a.handle('小婷', words)['reply']}\n")

        print("✅ 它带着外公的口吻、你们共同的回忆，在你想念时陪着你。")
        print("   —— 愿它帮你好好怀念，而不是代替那个真正的他。")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
