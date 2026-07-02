"""穴位按摩：头疼揉太阳穴、晕车掐内关、睡不着搓涌泉——常用穴位的位置、主治、怎么按。
图个日常保健、缓解小不适，简单好上手。纯数据 + 纯逻辑、可单测。

⚠️ 按摩是保健，不治病：手法轻柔、适可而止；孕妇有些穴位（合谷、三阴交）要避开；
不舒服明显或持续，还是看医生。
"""

from __future__ import annotations

# 穴位 -> (位置, [主治], 按法, 备注)
_POINTS = {
    "合谷": ("手背虎口，拇指和食指根部中间的肉鼓起处", ["头疼", "牙疼", "感冒", "面部不适"],
            "用另一手拇指按住，朝食指方向打圈按揉 1～2 分钟，酸胀为度。", "孕妇慎按。"),
    "太阳穴": ("眉梢和外眼角之间、向后约一指的凹陷处", ["头疼", "用眼疲劳", "提神"],
             "两手指腹轻轻打圈揉，别太用力。", ""),
    "风池": ("后脑勺两侧、发际边缘、两条大筋外侧的凹陷里", ["颈肩酸", "头疼", "落枕", "头晕"],
            "拇指顶住向上按揉，或双手抱头用拇指点按。", ""),
    "足三里": ("膝盖外侧凹陷往下约四指、小腿胫骨外侧一横指处", ["肠胃不适", "消化", "强身保健", "乏力"],
             "拇指按揉或握拳叩打，每侧 2～3 分钟。", "老话「常按足三里，胜吃老母鸡」。"),
    "内关": ("手腕横纹正中往上约三指、两条筋中间", ["恶心", "晕车", "心慌", "反胃"],
            "拇指掐按，晕车前或恶心时按，很管用。", ""),
    "涌泉": ("脚底前部凹陷处（脚趾弯曲时最凹的地方）", ["助眠", "降火", "安神", "脚凉"],
            "睡前用手心搓脚心，或拇指按揉，搓到发热。", ""),
    "迎香": ("鼻翼两侧、法令纹上的凹陷", ["鼻塞", "流涕", "不闻香臭"],
            "两食指上下搓揉鼻翼旁，搓热为度。", ""),
    "三阴交": ("内脚踝最高点往上约四指、胫骨后缘", ["睡眠", "妇科调理", "脾胃"],
             "拇指按揉，每侧 1～2 分钟。", "孕妇禁按。"),
    "神门": ("手腕横纹靠小指那一侧的凹陷", ["失眠", "心慌", "安神"],
            "拇指轻按揉，睡前按一按助眠。", ""),
    "印堂": ("两眉头正中间", ["提神醒脑", "头疼", "鼻塞"],
            "食指或中指点揉，或自下往上推抹。", ""),
    "攒竹": ("两眉头内侧的小凹陷", ["眼疲劳", "眼干", "头疼"],
            "拇指按住眉头轻轻揉按，看手机久了揉一揉。", ""),
    "肩井": ("脖子根和肩膀最高点连线的中点、肩膀肌肉最厚处", ["肩颈僵硬", "落枕", "酸痛"],
            "对侧手搭过来用四指拿捏、按揉。", "孕妇慎按。"),
}

# 不适 -> 推荐穴位（口语别名归一）
_SYMPTOM = {
    "头疼": ["太阳穴", "合谷", "风池"], "头痛": ["太阳穴", "合谷", "风池"], "头晕": ["风池"],
    "牙疼": ["合谷"], "牙痛": ["合谷"],
    "感冒": ["合谷", "迎香"], "鼻塞": ["迎香", "印堂"],
    "肠胃": ["足三里"], "胃": ["足三里", "内关"], "消化": ["足三里"], "反胃": ["内关"],
    "恶心": ["内关"], "晕车": ["内关"],
    "失眠": ["涌泉", "神门", "三阴交"], "睡不着": ["涌泉", "神门"], "助眠": ["涌泉", "神门"],
    "心慌": ["内关", "神门"], "颈": ["风池", "肩井"], "脖子": ["风池", "肩井"],
    "肩": ["肩井"], "落枕": ["风池", "肩井"], "眼": ["攒竹", "太阳穴"], "眼疲劳": ["攒竹"],
}

_CAVEAT = "（按摩是保健不治病，手法轻柔、适可而止；孕妇避开合谷三阴交；不适明显或持续请就医。）"


def _all(config=None) -> dict:
    d = {k: v for k, v in _POINTS.items()}
    cfg = (config or {}).get("acupoints") if isinstance(config, dict) else None
    extra = (cfg or {}).get("points") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                d[str(name)] = (str(v[0]), list(v[1]), str(v[2]), str(v[3]) if len(v) > 3 else "")
            elif isinstance(v, dict) and v.get("where"):
                d[str(name)] = (str(v["where"]), list(v.get("for") or []),
                                str(v.get("how", "")), str(v.get("note", "")))
    return d


def points(config=None) -> list:
    return list(_all(config).keys())


def find_point(utterance, config=None):
    """认出问的哪个穴位（名/带"穴"，最长匹配）。返回 (名, 元组) 或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for name in _all(config):
        if name in u and len(name) > best_len:
            best, best_len = name, len(name)
    return (best, _all(config)[best]) if best else None


def describe(name, config=None) -> str:
    """某穴位：位置 + 主治 + 按法 + 备注。查不到返回空。"""
    d = _all(config)
    if name not in d:
        return ""
    where, fors, how, note = d[name]
    body = f"{name}：在{where}。管{('、'.join(fors))}。按法：{how}"
    if note:
        body += note
    return body + _CAVEAT


def for_symptom(utterance, config=None) -> str:
    """哪儿不舒服按哪个穴。认不出返回空。"""
    u = str(utterance or "")
    hit = None
    for kw in sorted(_SYMPTOM, key=len, reverse=True):
        if kw in u:
            hit = kw
            break
    if not hit:
        return ""
    names = [n for n in _SYMPTOM[hit] if n in _all(config)]
    if not names:
        return ""
    parts = []
    for n in names:
        where, _f, how, _note = _all(config)[n]
        parts.append(f"{n}（{where}）：{how}")
    return f"{hit}可以揉这几个穴：" + "  ".join(parts) + _CAVEAT


def count(config=None) -> int:
    return len(_all(config))


def is_acupoint_query(utterance, config=None) -> bool:
    """是不是在问穴位/按摩保健。"""
    u = str(utterance or "")
    if find_point(u, config) and any(k in u for k in ("在哪", "怎么按", "按法", "位置", "什么穴",
                                                      "管啥", "管什么", "主治", "怎么揉", "穴")):
        return True
    # "头疼按哪个穴 / 失眠按摩哪"
    has_symptom = any(kw in u for kw in _SYMPTOM)
    if has_symptom and any(k in u for k in ("按哪", "按摩", "揉哪", "穴位", "按什么穴", "按哪个穴", "掐哪")):
        return True
    return False
