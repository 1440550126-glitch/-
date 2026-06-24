"""面部舵机：把"表情特征"翻译成每个面部舵机的脉宽，驱动机器人的脸真动起来。

expression_feedback 把心情变成 4 个量化特征（眉/眼/嘴角/嘴张）;这一块把它们映射到一张
拟人脸上的舵机（左右眉、左右眼皮、左右嘴角、下巴），算出每个舵机该给多少微秒脉宽，
带安全限位、带平滑过渡，通过可注入的 sender 发给硬件（PCA9685 / 串口 / ROS2）。

配合 expression_feedback 的视觉闭环：动作→舵机→脸→摄像头看回→比差→修正，
分身就能"边看自己边把表情调到位"，还会在舵机到了机械极限时如实说"调不动了"。

纯逻辑、可单测：没硬件时用 make_sim_face 造一对"舵机+摄像头"就能验证整条链路。
"""

from __future__ import annotations

# 默认面部舵机配置（一张拟人脸的常见排布）：
#   通道 -> (绑定的表情特征, 中位脉宽us, 行程span us, 方向±1, 安全下限us, 安全上限us)
# 特征量级：brow/eye/mouth_curve 约 -1..1；mouth_open 约 0..1。
DEFAULT_RIG = {
    "brow_l":   ("brow",        1500, 350, +1, 1050, 1950),
    "brow_r":   ("brow",        1500, 350, +1, 1050, 1950),
    "eyelid_l": ("eye",         1500, 350, +1, 1150, 1850),
    "eyelid_r": ("eye",         1500, 350, +1, 1150, 1850),
    "mouth_l":  ("mouth_curve", 1500, 350, +1, 1100, 1900),
    "mouth_r":  ("mouth_curve", 1500, 350, +1, 1100, 1900),
    "jaw":      ("mouth_open",  1200, 700, +1, 1150, 1950),
}


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def channels(rig=None) -> list:
    """这张脸有哪些舵机通道。"""
    return list((rig or DEFAULT_RIG).keys())


def neutral_pulses(rig=None) -> dict:
    """所有舵机回中位（放松脸）的脉宽。"""
    rig = rig or DEFAULT_RIG
    return {c: int(spec[1]) for c, spec in rig.items()}


def feature_to_pulses(actuation, rig=None) -> dict:
    """把表情特征 → 每个舵机的脉宽（带安全限位，绝不超出机械极限）。"""
    rig = rig or DEFAULT_RIG
    act = actuation or {}
    out = {}
    for ch, (feat, neutral, span, direction, lo, hi) in rig.items():
        v = float(act.get(feat, 0.0))
        pulse = neutral + direction * span * v
        out[ch] = int(round(_clamp(pulse, lo, hi)))
    return out


def pulses_to_features(pulses, rig=None) -> dict:
    """反过来：从舵机脉宽估回表情特征（同一特征的多个舵机取平均）。给"摄像头"和标定用。"""
    rig = rig or DEFAULT_RIG
    acc, cnt = {}, {}
    for ch, (feat, neutral, span, direction, _lo, _hi) in rig.items():
        if ch in (pulses or {}) and span:
            v = (float(pulses[ch]) - neutral) / (span * direction)
            acc[feat] = acc.get(feat, 0.0) + v
            cnt[feat] = cnt.get(feat, 0) + 1
    return {f: acc[f] / cnt[f] for f in acc}


def at_limit(pulses, rig=None, margin=2) -> list:
    """哪些舵机已经顶到安全限位（到机械极限了，再使劲也没用）。"""
    rig = rig or DEFAULT_RIG
    hit = []
    for ch, (_f, _n, _s, _d, lo, hi) in rig.items():
        p = (pulses or {}).get(ch)
        if p is None:
            continue
        if p <= lo + margin or p >= hi - margin:
            hit.append(ch)
    return hit


def drive(actuation, sender=None, rig=None) -> dict:
    """把一个表情直接发给舵机（全速到位，无平滑）。返回发出的脉宽；sender 出错不抛、返回脉宽即可。"""
    pulses = feature_to_pulses(actuation, rig)
    if sender is not None:
        try:
            sender(pulses)
        except Exception:
            pass
    return pulses


class FaceRig:
    """一张脸的舵机状态：记着每个舵机此刻在哪，朝目标'平滑'地挪（真舵机不能瞬移）。"""

    def __init__(self, rig=None, ease=0.5):
        self.rig = rig or DEFAULT_RIG
        self.ease = float(ease)
        self.current = neutral_pulses(self.rig)
        self.target = dict(self.current)

    def set_target(self, actuation):
        self.target = feature_to_pulses(actuation, self.rig)
        return self.target

    def step(self):
        """朝目标挪一步（ease 比例缓动）。返回此刻脉宽。"""
        for ch, tgt in self.target.items():
            cur = self.current.get(ch, tgt)
            self.current[ch] = int(round(cur + self.ease * (tgt - cur)))
        return dict(self.current)

    def settled(self, tol=2) -> bool:
        return all(abs(self.current.get(c, 0) - t) <= tol for c, t in self.target.items())

    def goto(self, actuation, sender=None, max_steps=12, tol=2):
        """平滑地把脸挪到某个表情，每步发一次。返回 (步数, 最终脉宽)。"""
        self.set_target(actuation)
        n = 0
        for _ in range(max(1, int(max_steps))):
            cur = self.step()
            n += 1
            if sender is not None:
                try:
                    sender(cur)
                except Exception:
                    pass
            if self.settled(tol):
                break
        return n, dict(self.current)


def make_recorder():
    """造一个记录用的 sender（没硬件时测试用）。返回 (sender, log)，log 里是每次发的脉宽。"""
    log = []

    def sender(pulses):
        log.append(dict(pulses))

    return sender, log


def robot_sender(robot):
    """把机器人的 face() 包成 sender；robot 没脸/没 face 方法就返回 None（优雅降级）。"""
    if robot is None or not hasattr(robot, "face") or not callable(getattr(robot, "face")):
        return None

    def sender(pulses):
        robot.face(pulses)

    return sender


def make_sim_face(rig=None, damping=0.8, bias=None, noise=0.0, seed=0):
    """造一对"模拟舵机 + 模拟摄像头"，验证整条链路（无硬件）。
    sender 记下舵机此刻脉宽（会被安全限位卡住）;camera 从脉宽估回脸上的真实特征——
    damping<1 表示"做出来没那么足"、bias 是这张脸天生的神态，逼着控制器多使劲、甚至顶到限位。
    """
    rig = rig or DEFAULT_RIG
    bias = dict(bias or {})
    state = {"pulses": neutral_pulses(rig), "n": int(seed)}

    def sender(pulses):
        state["pulses"] = dict(pulses)

    def camera(_actuation_ignored=None):
        feats = pulses_to_features(state["pulses"], rig)   # 摄像头看的是脸，不是你想做的动作
        out = {}
        for f, v in feats.items():
            x = damping * v + float(bias.get(f, 0.0))
            if noise:
                state["n"] = (state["n"] * 1103515245 + 12345) & 0x7FFFFFFF
                x += ((state["n"] / 0x7FFFFFFF) - 0.5) * 2 * noise
            out[f] = x
        return out

    return sender, camera


def express_on_face(emotion, sender, perceive=None, rig=None, gain=0.7,
                    steps=10, tol=0.08, config=None) -> dict:
    """把某个情绪做到机器人脸上。
    给了 perceive（摄像头）就走视觉闭环自我修正：动作→舵机→看回→修正→再来;
    没给就开环：直接把目标表情发给舵机。
    """
    from . import expression_feedback as ef
    rig = rig or DEFAULT_RIG
    emo = ef._key(emotion)
    if perceive is None:
        target = ef.target_features(emo, config)
        pulses = drive(target, sender, rig)
        return {"emotion": emo, "pulses": pulses, "closed_loop": False,
                "at_limit": at_limit(pulses, rig)}

    def render(act):
        drive(act, sender, rig)

    r = ef.self_correct(emo, perceive, render=render, gain=gain, steps=steps,
                        tol=tol, config=config)
    r["pulses"] = feature_to_pulses(r["actuation"], rig)
    r["at_limit"] = at_limit(r["pulses"], rig)
    r["closed_loop"] = True
    return r
