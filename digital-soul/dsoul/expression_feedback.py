"""表情自省：照镜子，自我修正。
分身把心情挂上脸（expression.py 给的神态）之后，还能"用眼睛看看自己脸上的表情到不到位"——
通过视觉读回当前真实的眉眼嘴，跟想要的样子比一比，差了就一点点往回调，直到神情对上。

这是一条"感知→动作"的闭环：想要的表情(target) → 做出来(actuation) → 看到的样子(observed) →
差多少(mismatch) → 修正(correct) → 再看……像人对着镜子把笑容调到位。

真正的"看"由外部视觉给（摄像头/截图 → 人脸特征），这里是可注入的 perceive；
纯逻辑、可单测：给个模拟的脸就能验证它会自己收敛。
"""

from __future__ import annotations

# 量化的脸部特征（都归一到约 -1..1）：
#   brow 眉（+扬 / -蹙锁）   eye 眼（+睁大 / -眯）
#   mouth_curve 嘴角（+上扬 / -下撇）   mouth_open 嘴张（0 闭 ~ 1 大张）
_FEATURES = ("brow", "eye", "mouth_curve", "mouth_open")

_FEATURE_CN = {"brow": "眉", "eye": "眼睛", "mouth_curve": "嘴角", "mouth_open": "嘴"}

# 情绪 → 想要的表情特征（和 expression.py 的神态描述对应）
_TARGETS = {
    "喜": {"brow": 0.2, "eye": -0.2, "mouth_curve": 0.8, "mouth_open": 0.1},
    "乐": {"brow": 0.3, "eye": -0.6, "mouth_curve": 1.0, "mouth_open": 0.6},
    "哀": {"brow": -0.5, "eye": -0.1, "mouth_curve": -0.7, "mouth_open": 0.0},
    "惧": {"brow": -0.4, "eye": 0.8, "mouth_curve": -0.2, "mouth_open": 0.4},
    "怒": {"brow": -0.8, "eye": 0.7, "mouth_curve": -0.3, "mouth_open": 0.0},
    "爱": {"brow": 0.1, "eye": 0.1, "mouth_curve": 0.5, "mouth_open": 0.05},
    "欲": {"brow": 0.4, "eye": 0.3, "mouth_curve": 0.2, "mouth_open": 0.0},
    "中": {"brow": 0.0, "eye": 0.0, "mouth_curve": 0.0, "mouth_open": 0.0},
}

_DEFAULT = "中"


def features() -> tuple:
    return _FEATURES


def _key(emotion) -> str:
    e = str(emotion or "").strip()
    return e if e in _TARGETS else _DEFAULT


def target_features(emotion, config=None) -> dict:
    """这个情绪"想要的"脸部特征。认不出按平和。可被 config.expression_targets 覆盖。"""
    t = dict(_TARGETS[_key(emotion)])
    cfg = (config or {}).get("expression_targets") if isinstance(config, dict) else None
    if isinstance(cfg, dict) and _key(emotion) in cfg and isinstance(cfg[_key(emotion)], dict):
        for f, v in cfg[_key(emotion)].items():
            if f in _FEATURES:
                t[f] = float(v)
    return t


def _clamp(x, lo=-1.5, hi=1.5) -> float:
    return lo if x < lo else hi if x > hi else x


def mismatch(target, observed) -> dict:
    """想要的 vs 看到的，差多少。返回每项差值 delta 和一个 0~1 的总分 score（越大越不像）。"""
    delta = {f: float(target.get(f, 0.0)) - float((observed or {}).get(f, 0.0)) for f in _FEATURES}
    # 均方根，再压到 0..1（特征量级约 ±1，2.0 封顶）
    rms = (sum(d * d for d in delta.values()) / len(_FEATURES)) ** 0.5
    return {"delta": delta, "score": min(1.0, rms / 2.0)}


def correct(actuation, target, observed, gain=0.6) -> dict:
    """按"看到的差距"修正动作：哪项没做到位，就往那个方向多使点劲（比例控制）。"""
    act = dict(actuation or {})
    for f in _FEATURES:
        cur = float(act.get(f, 0.0))
        gap = float(target.get(f, 0.0)) - float((observed or {}).get(f, 0.0))
        act[f] = _clamp(cur + gain * gap)
    return act


def read_expression(observed, config=None) -> str:
    """看着这张脸，最像哪种情绪（按特征最近邻）。给分身一句"我看着像在…"。"""
    obs = observed or {}
    best, best_d = _DEFAULT, None
    for emo in _TARGETS:
        t = target_features(emo, config)
        d = sum((t[f] - float(obs.get(f, 0.0))) ** 2 for f in _FEATURES)
        if best_d is None or d < best_d:
            best, best_d = emo, d
    return best


def self_correct(emotion, perceive, actuation=None, gain=0.6, steps=8,
                 tol=0.08, config=None, render=None) -> dict:
    """照镜子自我修正的闭环。
    perceive(actuation)->observed：外部"视觉"，看当前做出来的脸、读回特征（摄像头/截图）。
    render(actuation)：可选，先把当前动作"做出来"（如驱动面部舵机），再让 perceive 去看。
    一步步把动作往"想要的表情"上调，直到看着对了（score<=tol）或试够 steps 次。
    """
    target = target_features(emotion, config)
    act = dict(actuation) if actuation else {f: 0.0 for f in _FEATURES}
    trace = []
    last_score = 1.0
    for i in range(max(1, int(steps))):
        if render is not None:
            try:
                render(act)
            except Exception:
                pass
        observed = perceive(act) or {}
        m = mismatch(target, observed)
        last_score = m["score"]
        trace.append({"step": i, "observed": dict(observed), "score": round(last_score, 4),
                      "looks_like": read_expression(observed, config)})
        if last_score <= tol:
            break
        act = correct(act, target, observed, gain)
    return {"emotion": _key(emotion), "actuation": act, "trace": trace,
            "ok": last_score <= tol, "steps": len(trace), "final_score": round(last_score, 4)}


def make_mirror(damping=0.7, bias=None, noise=0.0, seed=0):
    """造一面"模拟的镜子"当 perceive 用（没真摄像头时演示/测试）：
    看到的 = damping*动作 + 这张脸天生的偏置 bias（比如总爱绷着、嘴角天生下垂）。
    damping<1 表示"做出来的没那么足"，分身得多使点劲才能让镜子里到位——正好考验自我修正。
    noise=0 时完全确定（可单测）。"""
    bias = dict(bias or {})
    state = {"n": int(seed)}

    def perceive(actuation) -> dict:
        out = {}
        for f in _FEATURES:
            v = damping * float((actuation or {}).get(f, 0.0)) + float(bias.get(f, 0.0))
            if noise:
                state["n"] = (state["n"] * 1103515245 + 12345) & 0x7FFFFFFF
                v += ((state["n"] / 0x7FFFFFFF) - 0.5) * 2 * noise
            out[f] = _clamp(v)
        return out

    return perceive


def describe(emotion, result, config=None) -> str:
    """把这次照镜子的结果说成人话。"""
    emo = _key(emotion)
    if not result or not result.get("trace"):
        return f"我想摆出「{emo}」的神情，可还没照上镜子。"
    if result.get("ok"):
        n = result.get("steps", 1)
        tail = "一下就到位了。" if n <= 1 else f"调了 {n} 次，神情对上了。"
        return f"照了照镜子，我把「{emo}」的表情摆到位了——{tail}"
    # 没完全到位：挑差得最多的那项说
    target = target_features(emo, config)
    observed = result["trace"][-1]["observed"]
    delta = mismatch(target, observed)["delta"]
    f = max(_FEATURES, key=lambda x: abs(delta[x]))
    name = _FEATURE_CN[f]
    more = "再使点劲" if delta[f] > 0 else "收一收"
    looks = result["trace"][-1].get("looks_like", emo)
    return (f"对着镜子调了调「{emo}」，镜子里还差点意思——{name}{more}（这会儿看着像在「{looks}」）。"
            "慢慢来，总能调对。")
