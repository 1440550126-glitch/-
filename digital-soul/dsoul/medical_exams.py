"""检查项目科普：医生开的 B 超、CT、核磁、胃镜……各查什么、要不要空腹、有没有辐射——
搞明白了去检查不发怵。纯逻辑、可单测。和"体检解读"(checkup 看数值)、"导诊"(triage 挂科)接着用，
这里讲'每项检查是干啥的'。

⚠️ 具体做哪项、怎么准备，听开单医生的;这里只是科普，帮你心里有数。
"""

from __future__ import annotations

# 检查 -> (查什么, 注意)
_EXAMS = {
    "B超": ("用超声波看肝、胆、胰、脾、肾、甲状腺、心脏、血管，也用于孕检。无辐射、无创、便宜，常用。",
          "查肝胆胰脾常要'空腹';查膀胱、妇科、前列腺常要'憋尿'。听单子上的准备要求。"),
    "X光": ("拍片，主要看骨头（骨折、关节）和肺。快、便宜。",
          "有少量辐射但很小、偶尔做没事;孕妇或可能怀孕要提前告诉医生。"),
    "CT": ("断层扫描，比 X 光看得细——肺结节、脑出血、肿瘤、结石等都靠它。",
         "辐射比普通 X 光大些、别频繁做;有的要打'造影剂'，过敏体质、肾不好要先告诉医生。"),
    "核磁共振": ("MRI，看脑子、脊髓、关节、软组织最清楚，没有辐射。",
             "时间长（一二十分钟）、机器噪音大、要躺着别动;体内有'心脏起搏器、金属植入物'的一般不能做，务必告知。"),
    "胃肠镜": ("一根带摄像头的细管直接看食管胃肠，能发现炎症、溃疡、息肉、早期肿瘤，还能当场取一点做化验。",
            "要'空腹'（胃镜）或'清肠'（肠镜，提前吃泻药）;怕难受可选'无痛'（打点麻醉），做完别马上开车。"),
    "心电图": ("查心跳节律和有没有心肌缺血，贴几个电极、几分钟就好，无创。",
            "怀疑阵发心律失常会让你戴'动态心电图'（Holter）背一整天，记录全天的心跳。"),
    "抽血化验": ("一管血能查好多：血常规、肝功、肾功、血糖、血脂、甲功、肿瘤标志物等。",
             "很多项要'空腹'（隔夜禁食 8 小时以上），查前别大鱼大肉别喝酒;抽完按住针眼几分钟。"),
    "尿便检查": ("验尿查泌尿、肾、血糖;验便查消化道出血、肠道问题。",
             "留样按要求来（如尿取'中段'）、别污染、及时送检。"),
}

_ALIAS = {
    "B超": "B超", "b超": "B超", "超声": "B超", "彩超": "B超", "做b超": "B超",
    "X光": "X光", "x光": "X光", "拍片": "X光", "拍个片": "X光", "胸片": "X光",
    "CT": "CT", "ct": "CT", "做ct": "CT", "CT检查": "CT",
    "核磁共振": "核磁共振", "核磁": "核磁共振", "磁共振": "核磁共振", "mri": "核磁共振", "MRI": "核磁共振",
    "胃肠镜": "胃肠镜", "胃镜": "胃肠镜", "肠镜": "胃肠镜", "做胃镜": "胃肠镜",
    "心电图": "心电图", "动态心电图": "心电图", "holter": "心电图",
    "抽血化验": "抽血化验", "抽血": "抽血化验", "验血": "抽血化验", "化验血": "抽血化验",
    "尿便检查": "尿便检查", "验尿": "尿便检查", "验便": "尿便检查", "大便检查": "尿便检查", "尿检": "尿便检查",
}


def _all(config=None) -> dict:
    d = dict(_EXAMS)
    cfg = (config or {}).get("medical_exams") if isinstance(config, dict) else None
    extra = (cfg or {}).get("exams") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("checks"):
                d[str(name)] = (str(v["checks"]), str(v.get("note", "")))
    return d


def exams(config=None) -> list:
    return list(_all(config).keys())


def find_exam(utterance, config=None):
    """认出问的哪项检查（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def info(exam, config=None) -> str:
    """某项检查查什么 + 注意 + 免责。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(exam or ""), str(exam or ""))
    if key not in d:
        return ""
    checks, note = d[key]
    return f"{key}：{checks}（注意：{note}）（具体怎么做、怎么准备听开单医生的。）"


def overview() -> str:
    """常见检查一览。"""
    return ("常见的检查：B 超（看脏器、无辐射）、X 光（看骨和肺）、CT（看得更细、辐射稍大）、"
            "核磁（看软组织、无辐射但时间长）、胃肠镜（直接看胃肠、能取活检）、心电图（查心脏）、"
            "抽血/验尿便（查各项指标）。想知道哪项查啥跟我说。")


def is_exam_query(utterance, config=None) -> bool:
    """是不是在问某项检查是干啥的。"""
    u = str(utterance or "")
    if find_exam(u, config) and any(k in u for k in ("查什么", "查啥", "是什么", "干啥", "要空腹",
                                                     "有辐射", "疼吗", "怎么做", "要注意", "啥意思",
                                                     "做啥", "为什么", "区别")):
        return True
    if any(k in u for k in ("做什么检查", "查什么检查", "检查项目")) and "检查" in u:
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
