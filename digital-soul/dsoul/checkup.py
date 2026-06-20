"""体检报告解读：化验单上一串箭头看不懂——这一块用大白话讲讲常见指标是啥、
高了低了大概意味着什么、平时注意点啥。让老人看完报告心里不发慌。

⚠️ 不替代医生：参考范围各家医院略有差别，确诊和用药一定听医生的。
这里只帮你看懂大方向、知道该不该上心。

纯数据 + 纯逻辑、可单测。可在 config 的 checkup 里补自家关心的指标。
"""

from __future__ import annotations

# (规范名, [别名/缩写], 正常大致范围, 偏高含义, 偏低含义, 平时提示)
_ITEMS = [
    ("血压", ["高压", "低压", "血压值"],
     "理想约 120/80 mmHg 上下；高压持续≥140 或低压≥90 算偏高。",
     "偏高是高血压，伤心脑肾血管，要长期管住——按时吃降压药、少盐。",
     "偏低若伴头晕乏力要留意，蹲起慢一点。",
     "在家定点量、记下来给医生看最有用。"),
    ("空腹血糖", ["血糖", "空腹血糖值", "FPG"],
     "正常约 3.9～6.1 mmol/L；≥7.0（两次）提示糖尿病。",
     "偏高警惕糖尿病/糖前期，控糖、迈开腿、管住嘴，复查糖化。",
     "偏低（<3.9）会心慌手抖出汗，赶紧吃点糖/饼干，糖尿病人尤其防低血糖。",
     "抽血前别吃东西，空腹 8 小时以上。"),
    ("糖化血红蛋白", ["糖化", "HbA1c"],
     "正常约 4%～6%；反映近 2～3 个月的平均血糖。",
     "偏高说明这阵子血糖总体偏高，比单次血糖更说明问题。",
     "偏低少见，问医生。",
     "糖尿病人盯这个比盯单次血糖更准。"),
    ("总胆固醇", ["胆固醇", "TC"],
     "一般建议 <5.2 mmol/L。",
     "偏高是血脂高的一种，增加动脉硬化、冠心病风险，少油腻、多运动。",
     "偏低一般问题不大，太低问医生。",
     "抽血前一晚清淡、别大鱼大肉。"),
    ("甘油三酯", ["TG", "血脂甘油三酯"],
     "一般建议 <1.7 mmol/L。",
     "偏高和高油高糖高酒关系大，管住嘴、戒酒、减重最见效。",
     "偏低多无碍。",
     "查前三天别喝酒、别大餐。"),
    ("低密度脂蛋白", ["低密度", "LDL", "坏胆固醇"],
     "一般 <3.4；有心血管病/高危更要压到更低。",
     "就是「坏胆固醇」，偏高最伤血管，医生可能让吃他汀。",
     "偏低通常是好事。",
     "这项是血脂里最该盯的。"),
    ("高密度脂蛋白", ["高密度", "HDL", "好胆固醇"],
     "一般 >1.0 较好，越高越护血管。",
     "偏高是好事，说明血管清道夫多。",
     "偏低（太少）反而不利，多运动能升一升。",
     "这项是「越高越好」的那个。"),
    ("尿酸", ["UA", "血尿酸"],
     "男约 <420、女约 <360 μmol/L。",
     "偏高易痛风、长尿酸结石，少喝啤酒、少吃海鲜动物内脏、多喝水。",
     "偏低少见，一般不碍事。",
     "痛风发作时关节红肿痛得厉害，及时就医。"),
    ("谷丙转氨酶", ["ALT", "转氨酶", "肝功"],
     "一般 <40 U/L 上下。",
     "偏高提示肝细胞受损（脂肪肝、喝酒、熬夜、某些药都会），别熬夜戒酒复查。",
     "偏低一般无碍。",
     "查前别喝酒、别剧烈运动。"),
    ("谷草转氨酶", ["AST", "GOT"],
     "一般 <40 U/L 上下，常和谷丙一起看肝。",
     "偏高同样提示肝（或心肌）受损，结合谷丙一起看。",
     "偏低一般无碍。",
     "和谷丙转氨酶搭着看更准。"),
    ("肌酐", ["Cr", "血肌酐"],
     "男约 59～104、女约 45～84 μmol/L，反映肾功能。",
     "偏高警惕肾功能下降，少憋尿、别乱吃伤肾的药/保健品，复查。",
     "偏低多见于肌肉少，问题不大。",
     "肾的事别拖，发现高了找肾内科。"),
    ("尿素氮", ["BUN", "尿素"],
     "一般约 2.9～8.2 mmol/L，也看肾。",
     "偏高可能肾功能或脱水/高蛋白饮食，结合肌酐一起看。",
     "偏低多无碍。",
     "和肌酐一起评估肾。"),
    ("血红蛋白", ["血色素", "Hb"],
     "男约 130～175、女约 115～150 g/L。",
     "偏高少见（缺氧、脱水等），问医生。",
     "偏低是贫血，乏力面色差，查清原因、补铁或对因治疗。",
     "老人贫血别大意，可能藏着别的病。"),
    ("白细胞", ["WBC", "白血球"],
     "约 3.5～9.5 ×10⁹/L。",
     "偏高常见于感染、炎症，结合症状看。",
     "偏低要留意免疫力/某些药影响，复查。",
     "光一个数不说明问题，要结合人。"),
    ("血小板", ["PLT"],
     "约 125～350 ×10⁹/L。",
     "偏高问医生（脱水、炎症等）。",
     "偏低易出血、瘀斑，明显降低要重视。",
     "牙龈老出血、身上无故青紫，查查它。"),
    ("体重指数", ["BMI", "体质指数"],
     "正常约 18.5～23.9；≥24 超重，≥28 肥胖。",
     "偏高是超重/肥胖，伤关节、招三高，慢慢减、迈开腿。",
     "偏低是偏瘦，注意营养够不够。",
     "BMI = 体重(kg) ÷ 身高(m) 的平方。"),
]


def _all(config=None) -> list:
    items = list(_ITEMS)
    cfg = (config or {}).get("checkup") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 6:
                items.append(tuple(str(x) if not isinstance(x, list) else x for x in it[:6]))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []),
                              str(it.get("normal", "")), str(it.get("high", "")),
                              str(it.get("low", "")), str(it.get("tip", ""))))
    return items


def items(config=None) -> list:
    """所有指标的规范名。"""
    return [it[0] for it in _all(config)]


def find_item(utterance, config=None):
    """从话里认出问的是哪个指标（规范名或别名，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    table = _all(config)
    best, best_len = None, 0
    for it in table:
        for name in [it[0]] + list(it[1]):
            if name and name in u and len(name) > best_len:
                best, best_len = it, len(name)
    return best


def direction(utterance) -> str:
    """听出是问「高」还是「低」；听不出返回空（默认整体讲）。"""
    u = str(utterance or "")
    if any(k in u for k in ("高", "偏高", "↑", "超标", "上箭头")):
        return "high"
    if any(k in u for k in ("低", "偏低", "↓", "少", "下箭头")):
        return "low"
    return ""


def interpret(utterance, config=None) -> str:
    """解读一句：认出指标 → 按高/低（或整体）讲含义 + 提示 + 免责。认不出返回空。"""
    it = find_item(utterance, config)
    if not it:
        return ""
    name, _alias, normal, high, low, tip = it
    # 去掉指标名本身再判方向，免得「低密度」「高密度」里的高/低被误当成箭头方向
    u = str(utterance or "")
    for nm in sorted([name] + list(_alias), key=len, reverse=True):
        u = u.replace(nm, "")
    d = direction(u)
    if d == "high":
        body = f"{name}偏高：{high}"
    elif d == "low":
        body = f"{name}偏低：{low}"
    else:
        body = f"{name}：{normal} {high}"
    extra = f" {tip}" if tip else ""
    return f"{body}{extra}（参考范围各医院略有差别，确诊用药听医生的。）"


def is_checkup_query(utterance, config=None) -> bool:
    """是不是在问体检报告/某项指标。"""
    u = str(utterance or "")
    if any(k in u for k in ("体检报告", "化验单", "化验结果", "检查报告", "报告单")):
        return True
    # 点了某个指标 + 解读意图
    if find_item(u, config) and any(k in u for k in ("高", "低", "什么意思", "啥意思", "正常吗",
                                                     "怎么回事", "要紧吗", "严重吗", "解读", "看看",
                                                     "超标", "箭头", "咋办", "怎么办")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
