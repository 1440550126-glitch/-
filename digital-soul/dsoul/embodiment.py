"""给机器身体注入灵魂：让动作带着情绪与心意——你说话它转头看你、你难过它放缓靠近、
高兴时点头前倾、守护时挡在身前。闲着也"活着"（像呼吸般轻动、环顾），不是僵着的铁疙瘩。

把 Agent 的内在状态（七情 / 注意 / 守护）映射成机器人的体态与目光。
纯逻辑、可单测（SimulationRobot 打印，真实/ROS2 机器人按同一接口驱动）。
"""

from __future__ import annotations

# 七情 → (体态/手势, 细节)
_BODY = {
    "喜": ("点头前倾", "嘴角扬起，身子微微凑近"),
    "乐": ("轻快点头", "肩膀放松，带着笑意"),
    "哀": ("放缓垂首", "声音放轻，缓缓靠近一点"),
    "惧": ("收拢戒备", "微挡在你身前，留意四周"),
    "爱": ("温柔倾身", "目光柔和，朝你侧过身"),
    "怒": ("稳住站定", "不动声色，站得更稳"),
    "恶": ("微微侧身", "略一蹙眉，拉开半步"),
    "欲": ("身子前探", "眼里有光，凑近些"),
}

_IDLE = [
    ("轻轻起伏", "像呼吸般微微起落，活着的样子"),
    ("缓缓环顾", "目光在屋里轻轻扫过，留意着家人"),
    ("微微侧头", "像在想事，又像在听屋里的动静"),
    ("整理姿态", "把身子摆正，安安静静守着"),
]

# 待机时的神态也随心情（焦虑就坐立不安、欢喜就带点雀跃）
_MOOD_IDLE = {
    "哀": ("静静出神", "垂着头，像在想念什么"),
    "惧": ("微微不安", "身子轻轻晃，时不时看向门口"),
    "怒": ("沉着收敛", "站得笔直，慢慢把气喘匀"),
    "喜": ("轻轻晃悠", "像哼着调子，带点雀跃"),
    "乐": ("轻轻晃悠", "像哼着调子，带点雀跃"),
    "爱": ("柔和守望", "目光软软地落在家人待的方向"),
}


def body_language(emotion):
    """某个情绪对应的体态。未知情绪给一个平和的默认。"""
    return _BODY.get(emotion, ("自然站立", "平和地待着"))


def _do_gesture(robot, name, detail="") -> None:
    if robot is None:
        return
    fn = getattr(robot, "gesture", None)
    if callable(fn):
        try:
            fn(name, detail)
        except Exception:
            pass


def attend(robot, speaker) -> None:
    """有人说话/出现，转头看向 TA（专注地听）。"""
    if robot is not None and speaker:
        try:
            robot.look_at(speaker)
        except Exception:
            pass


def express(robot, emotion=None, speaker=None) -> None:
    """把情绪与注意用身体表达出来：先看向人，再做出体态；难过时还轻轻靠近。"""
    if robot is None:
        return
    attend(robot, speaker)
    name, detail = body_language(emotion)
    _do_gesture(robot, name, detail)
    if emotion in ("哀", "惧"):          # 你不好受，身体也凑近一点，陪着你
        try:
            robot.move("前", 0.3)
        except Exception:
            pass


def idle(robot, seed="", mood=None) -> None:
    """闲时的"活着"微动作，让它不像僵着的铁疙瘩；心情明显时神态也随之变。"""
    if robot is None:
        return
    if mood in _MOOD_IDLE:
        name, detail = _MOOD_IDLE[mood]
    else:
        name, detail = _IDLE[len(str(seed)) % len(_IDLE)]
    _do_gesture(robot, name, detail)


def wake(robot) -> None:
    """魂醒在身体里：开机时缓缓"醒来"，舒展、环顾这个家。"""
    if robot is None:
        return
    _do_gesture(robot, "缓缓醒来", "像睁开眼，舒展一下，环顾这个家")
    try:
        robot.look_at("这个家")
    except Exception:
        pass


def approach(robot, target) -> None:
    """有人进门，迎上前去（张开怀抱似的暖）。"""
    if robot is None or not target:
        return
    try:
        robot.look_at(target)
    except Exception:
        pass
    _do_gesture(robot, "迎上前", f"朝{target}迎过去，像张开怀抱")
    try:
        robot.move("前", 0.5)
    except Exception:
        pass


def guard_stance(robot, target) -> None:
    """守护谁，就用身体挡在前头。"""
    if robot is None or not target:
        return
    _do_gesture(robot, "挡在身前", f"侧身护住{target}，目光警觉")
    try:
        robot.protect(target)
    except Exception:
        pass
