"""书信格式：写封信、写张贺卡，称呼怎么起、问候怎么说、'此致敬礼'写哪儿、落款怎么落——
一封得体的信有讲究。把格式说清楚，长辈写信不露怯，晚辈也学个规矩。纯逻辑、可单测。
和"代笔家书"(letters 替你写内容)接着用，这里讲"格式怎么摆"。
"""

from __future__ import annotations

# 部分 -> 怎么写
_PARTS = {
    "称呼": "信的第一行、顶格写，后面加冒号。长辈用'敬爱的爷爷:'、平辈'亲爱的老张:'、"
          "一般场合'尊敬的X先生/女士:'。称呼要得体、亲切。",
    "问候语": "称呼下一行、空两格写句问候，如'您好！''近来身体可好？''好久不见，甚是想念。'"
           "暖个场再说正事。",
    "正文": "再另起一段、每段开头空两格，把要说的事一段段写清楚；先重点后细节，语气随对象，"
          "给长辈恭敬些、给朋友随和些。",
    "祝颂语": "正文写完另起，写祝福话。最常用'此致'（接正文后或另起空两格），下一行顶格写'敬礼!'。"
           "给长辈可用'敬祝 身体健康、福寿安康'；'顺颂 时祺'也得体。",
    "署名": "信的右下角写上自己的名字；给长辈署名前加身份，如'孙 小明''晚 李四'，显谦敬。",
    "日期": "署名的下一行（也在右下），写上'年 月 日'，别漏。",
    "信封": "正面写收信人地址、姓名（中间偏上）、邮编；背面或左上写寄信人地址姓名。"
          "姓名后给长辈可写'敬启'、平辈'收'。",
}

# 贺卡（简短版）
_CARD = ("贺卡比信短：①顶上写称呼（'敬爱的老师:'）；②中间一两句应景的祝福话；"
         "③右下角署名 + 日期。短短几句，心意到了就好。")

_ALIAS = {
    "称呼": "称呼", "抬头": "称呼", "开头怎么写": "称呼",
    "问候语": "问候语", "问候": "问候语",
    "正文": "正文", "内容怎么写": "正文",
    "祝颂语": "祝颂语", "此致敬礼": "祝颂语", "此致": "祝颂语", "敬礼": "祝颂语", "结尾": "祝颂语", "祝福语怎么写": "祝颂语",
    "署名": "署名", "落款": "署名", "签名怎么写": "署名",
    "日期": "日期", "写日期": "日期",
    "信封": "信封", "信封怎么写": "信封", "收信人": "信封", "邮编": "信封",
}


def _all(config=None) -> dict:
    d = dict(_PARTS)
    cfg = (config or {}).get("letter_format") if isinstance(config, dict) else None
    extra = (cfg or {}).get("parts") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def parts(config=None) -> list:
    return list(_all(config).keys())


def find_part(utterance, config=None):
    """认出问书信的哪一部分（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def explain(part, config=None) -> str:
    """某一部分怎么写。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(part or ""), str(part or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}"


def card_format() -> str:
    """贺卡怎么写。"""
    return _CARD


def overview() -> str:
    """一封信从上到下的格式。"""
    return ("一封信从上到下：①称呼（顶格 + 冒号）；②问候语（空两格）；③正文（每段空两格）；"
            "④祝颂语（'此致'接后、下一行顶格'敬礼!'，给长辈用'敬祝健康'）；"
            "⑤署名（右下，对长辈加'孙/晚'）；⑥日期（署名下一行）。想细说哪部分跟我说。")


def is_letter_query(utterance, config=None) -> bool:
    """是不是在问书信/贺卡格式。"""
    u = str(utterance or "")
    if any(k in u for k in ("书信格式", "写信格式", "信怎么写", "写信怎么", "贺卡怎么写", "贺卡格式")):
        return True
    if find_part(u, config) and any(k in u for k in ("怎么写", "写哪", "格式", "怎么落", "放哪",
                                                     "是什么", "怎么起", "咋写")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
