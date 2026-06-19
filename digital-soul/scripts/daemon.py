#!/usr/bin/env python3
"""一键常驻服务：同时跑「持续感知（摄像头主动打招呼）」+「定时睡眠巩固」。

适合部署到树莓派 / 机器人，配合 systemd 开机自启（见 docs/deploy.md）。

用法：
  python scripts/daemon.py                    # 感知 + 每 8 小时巩固
  python scripts/daemon.py --sleep-every 6    # 每 6 小时巩固
  python scripts/daemon.py --no-vision        # 不开摄像头，仅定时巩固
  python scripts/daemon.py --robot ros2       # 动作走 ROS2 机器人
  python scripts/daemon.py --voice            # 看 + 听 + 说（全感官）
  python scripts/daemon.py --web              # 顺带开手机网页状态页(默认 8765)
"""

import argparse
import pathlib
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402
from dsoul.presence import PresenceMonitor  # noqa: E402
from dsoul.voice import Ears, Mouth, record_wav  # noqa: E402


def start_vision(agent, mouth=None) -> bool:
    me = agent.identity.get("name", "我")

    def on_enter(name: str) -> None:
        from dsoul.embodiment import approach
        approach(getattr(agent, "robot", None), name)   # 有人进门，身体先迎上前去
        text = agent.greet(name)   # 清晨第一次见到主人会自动带上"晨间简报"
        # 注：挂了 agent.mouth 时，greet 内部已"说动合一"地出声，这里不再重复念
        print(f"[感知] {name} 进入画面 → {me}: {text}", flush=True)
        if mouth is not None and getattr(agent, "mouth", None) is None:
            mouth.speak(text, mood=_mood(agent), profile=agent.identity.get("voice"))
        for n in agent.fire_event("enter", name):   # 进门自动化（"我一进门就开灯"）
            print(f"[自动化] {n}", flush=True)
            if mouth is not None:
                mouth.speak(n)

    def on_leave(name: str) -> None:
        print(f"[感知] {name} 离开画面", flush=True)

    mon = PresenceMonitor(agent.perception, on_enter=on_enter, on_leave=on_leave)
    if not mon.available:
        print("[感知] 摄像头 / 人脸识别不可用，跳过视觉。", flush=True)
        return None
    threading.Thread(target=mon.run, daemon=True).start()
    print("[感知] 摄像头持续感知已启动。", flush=True)
    return mon


def _mood(agent):
    try:
        return agent.emotions.mood()[0] if getattr(agent, "emotions", None) else None
    except Exception:
        return None


def _owner(agent) -> str:
    for p in agent.authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return agent.identity.get("name", "我")


def voice_loop(agent, ears, mouth, monitor, wake=None) -> None:
    """持续聆听：听到话 → 结合"当前画面里的人"判断说话人 → 回应并播报。

    设了唤醒词（如"贾维斯"）则只在被点名时回应，更像贴身管家。
    """
    me = agent.identity.get("name", "我")
    owner = _owner(agent)
    tip = f"（说「{wake}」唤醒）" if wake else ""
    print(f"[语音] 持续聆听已启动{tip}。", flush=True)
    while True:
        wav = record_wav(5)
        if wav is None:
            print("[语音] 没有麦克风（缺 sounddevice），停止语音。", flush=True)
            return
        text = ears.transcribe(wav)
        if not text:
            continue
        if wake:  # 只在被点名时回应
            if wake not in text:
                continue
            text = text.replace(wake, "", 1).strip("，,。.!！?？、 ")
            if not text:
                mouth.speak(f"在的，有什么吩咐？")
                continue
        speaker = (monitor.current_speaker() if monitor else None) or owner
        print(f"[语音] {speaker}: {text}", flush=True)
        res = agent.handle(speaker, text)
        print(f"[语音] {me}: {res['reply']}", flush=True)
        # 说动合一：边说边动，声音按节拍一句句出（带情绪 + 本人嗓音）
        from dsoul.perform import perform_spoken
        perform_spoken(res["reply"], emotion=_mood(agent), robot=getattr(agent, "robot", None),
                       mouth=mouth, profile=agent.identity.get("voice"), cues=True)


def sleep_loop(agent, hours: float) -> None:
    while True:
        time.sleep(hours * 3600)
        rep = Consolidator(
            agent.memory, agent.journal, llm=agent.llm,
            identity=agent.identity, authority=agent.authority,
        ).run()
        print(f"[睡眠] 巩固 {rep['processed']} 条 → 新增 {len(rep['learned'])} 条记忆", flush=True)
        if hasattr(agent, "dream"):
            d = agent.dream()
            if d:
                print(f"[梦境] {d}", flush=True)


def trigger_loop(agent, mouth=None) -> None:
    """每 30 秒检查一次定时自动化（如"每天22点提醒锁门"）与守护提醒（吃药/复查）。"""
    while True:
        time.sleep(30)
        try:
            notices = agent.check_time_triggers() + agent.check_conditions()
        except Exception as e:
            print(f"[自动化] 出错：{e}", flush=True)
            notices = []
        profile = agent.identity.get("voice")
        for n in notices:
            print(f"[自动化] {n}", flush=True)
            if mouth is not None:
                mouth.speak(n, mood=_mood(agent), profile=profile)
        try:
            for task in agent.pop_due_reminders():       # 随口设的提醒到点了
                line = f"提醒你：{task}。"
                print(f"[提醒] {line}", flush=True)
                if mouth is not None:
                    mouth.speak(line, mood=_mood(agent), profile=profile)
        except Exception as e:
            print(f"[提醒] 出错：{e}", flush=True)
        try:
            cares = agent.due_care()
        except Exception as e:
            print(f"[守护] 出错：{e}", flush=True)
            cares = []
        for c in cares:
            print(f"[守护] {c}", flush=True)
            if mouth is not None:                       # 用 TA 本人的嗓音叮嘱家人
                mouth.speak(c, mood=_mood(agent), profile=profile)
        try:
            caps = agent.due_capsules()
        except Exception as e:
            print(f"[胶囊] 出错：{e}", flush=True)
            caps = []
        for cap in caps:
            print(f"[时光胶囊] {cap}", flush=True)
            if mouth is not None:
                mouth.speak(cap, mood=_mood(agent), profile=profile)
        # 老伴专属：到日常时辰唤一句默契；入夜主动道一声晚安（各自去重）
        try:
            spouse_lines = []
            r = agent.spouse_ritual_now()
            if r:
                spouse_lines.append(r)
            gn = agent.nightly_goodnight()
            if gn:
                spouse_lines.append(gn)
        except Exception as e:
            print(f"[老伴] 出错：{e}", flush=True)
            spouse_lines = []
        for line in spouse_lines:
            print(f"[老伴] {line}", flush=True)
            if mouth is not None:
                mouth.speak(line, mood=_mood(agent), profile=profile)
        # 陪伴守护：到点了主动提醒吃饭/活动/睡觉（present-tense，每时段一次）
        try:
            wb = agent.wellbeing_nudge()
        except Exception as e:
            print(f"[陪伴] 出错：{e}", flush=True)
            wb = ""
        if wb:
            print(f"[陪伴] {wb}", flush=True)
            if mouth is not None:
                mouth.speak(wb, mood=_mood(agent), profile=profile)
        # 守护：到点吃药 / 临近就医，主动提醒（按天去重）
        try:
            health = agent.proactive_health_reminders()
        except Exception as e:
            print(f"[守护] 出错：{e}", flush=True)
            health = []
        for line in health:
            print(f"[守护] {line}", flush=True)
            if mouth is not None:
                mouth.speak(line, mood=_mood(agent), profile=profile)
        # 小确幸：傍晚主动问一句今天的开心事（每天一次）
        try:
            joy_q = agent.joy_evening_prompt()
        except Exception as e:
            print(f"[小确幸] 出错：{e}", flush=True)
            joy_q = ""
        if joy_q:
            print(f"[小确幸] {joy_q}", flush=True)
            if mouth is not None:
                mouth.speak(joy_q, mood=_mood(agent), profile=profile)
        # 习惯陪练：傍晚催一句今天还没打卡的好习惯（每天一次）
        try:
            hb = agent.habit_evening_reminder()
        except Exception as e:
            print(f"[习惯] 出错：{e}", flush=True)
            hb = ""
        if hb:
            print(f"[习惯] {hb}", flush=True)
            if mouth is not None:
                mouth.speak(hb, mood=_mood(agent), profile=profile)
        # 养花：该浇水时提醒一句（每天一次）
        try:
            pw = agent.plant_due_reminder()
        except Exception as e:
            print(f"[养花] 出错：{e}", flush=True)
            pw = ""
        if pw:
            print(f"[养花] {pw}", flush=True)
            if mouth is not None:
                mouth.speak(pw, mood=_mood(agent), profile=profile)
        # 养宠：到点喂食/该遛了，提醒一句
        try:
            pet = agent.pet_due_reminders()
        except Exception as e:
            print(f"[养宠] 出错：{e}", flush=True)
            pet = ""
        if pet:
            print(f"[养宠] {pet}", flush=True)
            if mouth is not None:
                mouth.speak(pet, mood=_mood(agent), profile=profile)
        # 常联系：好久没联系的亲友，提醒一句（每天一次）
        try:
            kit = agent.touch_due_reminder()
        except Exception as e:
            print(f"[常联系] 出错：{e}", flush=True)
            kit = ""
        if kit:
            print(f"[常联系] {kit}", flush=True)
            if mouth is not None:
                mouth.speak(kit, mood=_mood(agent), profile=profile)


def think_loop(agent, minutes: float) -> None:
    """自主心跳：定期反思 + 跟进欠账。"""
    while True:
        time.sleep(minutes * 60)
        try:
            out = agent.tick()
        except Exception as e:
            print(f"[自主] tick 出错：{e}", flush=True)
            continue
        for notice in out.get("notices", []):
            print(f"[自主] {notice}", flush=True)
        # 主动牵挂：自己琢磨着谁有阵子没露面、上回有心事，捎句话过去
        try:
            intents = agent.reach_out_intents()
        except Exception as e:
            print(f"[牵挂] 出错：{e}", flush=True)
            intents = []
        for _name, msg in intents:
            print(f"[牵挂] {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep-every", type=float, default=8.0, help="每 N 小时巩固一次")
    ap.add_argument("--think-every", type=float, default=30.0, help="每 N 分钟自主反思/跟进一次")
    ap.add_argument("--no-vision", action="store_true", help="不启用摄像头感知")
    ap.add_argument("--robot", choices=["sim", "ros2"], default="sim", help="动作执行后端")
    ap.add_argument("--voice", action="store_true", help="启用语音对话（听 + 说）")
    ap.add_argument("--wake", default=None, help="唤醒词（如 贾维斯）；设置后只在被点名时回应")
    ap.add_argument("--web", nargs="?", const=8765, type=int, default=None,
                    help="开启网页状态页（可指定端口，默认 8765）")
    args = ap.parse_args()

    robot = None
    if args.robot == "ros2":
        from dsoul.ros2_robot import Ros2Robot

        robot = Ros2Robot()
    agent = build_agent(robot=robot)

    from dsoul.embodiment import wake
    wake(agent.robot)   # 魂醒在身体里：缓缓"醒来"，舒展、环顾这个家

    me = agent.identity.get("name", "我")
    llm = "✅" if agent.llm.available else "降级"
    print(
        f"🤖 {me} 的数字分身常驻服务启动 ｜ 大模型:{llm} ｜ 记忆 {len(agent.memory.items)} 条"
        f" ｜ 机器人:{args.robot}",
        flush=True,
    )

    mouth = Mouth() if args.voice else None   # 语音模式下，连打招呼/晨报也念出来
    agent.mouth = mouth                        # 挂上"嘴"：主动说的话也出声，且说动合一
    monitor = start_vision(agent, mouth) if not args.no_vision else None

    if args.web is not None:
        from dsoul.webstatus import start_web

        start_web(agent, monitor, args.web)
        print(f"🌐 网页状态页：http://<本机IP>:{args.web}/ （手机同一局域网可访问）", flush=True)

    threading.Thread(target=sleep_loop, args=(agent, args.sleep_every), daemon=True).start()
    print(f"🌙 每 {args.sleep_every} 小时自动巩固一次。", flush=True)
    threading.Thread(target=think_loop, args=(agent, args.think_every), daemon=True).start()
    print(f"🧠 每 {args.think_every} 分钟自主反思 / 跟进一次。", flush=True)
    threading.Thread(target=trigger_loop, args=(agent, mouth), daemon=True).start()
    print("⏰ 定时自动化已启用（每 30 秒检查）。Ctrl+C 退出。", flush=True)

    try:
        if args.voice:
            ears = Ears()
            print(f"[语音] 听:{ears.backend or '无'} ｜ 说:{mouth.backend or '无(打印)'}", flush=True)
            if ears.available:
                voice_loop(agent, ears, mouth, monitor, wake=args.wake)
            else:
                print("[语音] 未装语音转文字(faster-whisper)，无法聆听；保留感知+巩固。", flush=True)
                while True:
                    time.sleep(3600)
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
