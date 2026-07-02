"""看懂天气预报：降水概率是啥意思、预警颜色哪个重、空气质量多少算好、风力几级什么概念——
天气预报里的词儿弄明白，出门心里有数。纯数据 + 纯逻辑、可单测。
和"今天穿啥"(weather_day 按温度给穿衣建议)接着用，这里专管"看懂那些词"。
"""

from __future__ import annotations

# 名词 -> (通俗解释)
_TERMS = {
    "降水概率": "比如'降水概率 60%'，不是下 60% 的雨，是'有六成可能会下雨'。概率高就带把伞稳妥。",
    "预警信号": "按严重程度从轻到重是：蓝→黄→橙→红。红色最危险（如红色暴雨/台风），尽量别出门。"
              "常见有暴雨、台风、高温、寒潮、大雾、雷电、大风、霜冻预警。",
    "空气质量": "看 AQI 指数：0–50 优、51–100 良、101–150 轻度、151–200 中度、201–300 重度、300 以上严重。"
              "主要看 PM2.5;污染重了少出门、戴口罩、关窗。",
    "紫外线指数": "弱（1–2）不用管；中等（3–5）戴帽；强（6–7）、很强（8–10）、极强（11+）要打伞抹防晒，避开正午暴晒。",
    "风力等级": "3 级树叶摇、5 级小树晃、6 级打伞困难、7–8 级走路费劲折树枝、10 级以上能掀屋顶。"
              "大风天关好门窗、收好阳台东西、少骑车。",
    "体感温度": "算上湿度和风的'实际感觉'温度：夏天湿度大会比气温更闷热，冬天有风会比气温更冷。"
              "穿衣按体感来更靠谱。",
    "相对湿度": "空气里水汽的饱和程度。太高（>70%）闷湿、晾衣服不干；太低（<30%）干燥、易上火咳嗽，可加湿。",
    "生活指数": "预报里的'穿衣指数、感冒指数、晾晒指数、洗车指数'等，是按天气给的生活建议，照着安排省心。",
    "霜冻预报": "气温降到 0℃ 上下、地面要结霜，地里的菜要盖、水管要包、路面或结冰防滑。",
    "高温预警": "日最高气温要到 35℃（橙色 37℃、红色 40℃）以上，避开午后高温、多喝水防中暑、看护好老人小孩。",
}

_ALIAS = {
    "降水概率": "降水概率", "降水率": "降水概率", "下雨概率": "降水概率", "降雨概率": "降水概率",
    "预警信号": "预警信号", "预警颜色": "预警信号", "红色预警": "预警信号", "橙色预警": "预警信号",
    "黄色预警": "预警信号", "蓝色预警": "预警信号", "天气预警": "预警信号",
    "空气质量": "空气质量", "AQI": "空气质量", "aqi": "空气质量", "PM2.5": "空气质量", "pm2.5": "空气质量", "雾霾": "空气质量",
    "紫外线指数": "紫外线指数", "紫外线": "紫外线指数",
    "风力等级": "风力等级", "几级风": "风力等级", "风力": "风力等级", "风级": "风力等级",
    "体感温度": "体感温度", "体感": "体感温度",
    "相对湿度": "相对湿度", "湿度": "相对湿度",
    "生活指数": "生活指数", "穿衣指数": "生活指数", "感冒指数": "生活指数", "晾晒指数": "生活指数",
    "霜冻": "霜冻预报", "霜冻预报": "霜冻预报",
    "高温预警": "高温预警", "高温橙色": "高温预警", "高温红色": "高温预警",
}


def _all(config=None) -> dict:
    d = dict(_TERMS)
    cfg = (config or {}).get("weather_terms") if isinstance(config, dict) else None
    extra = (cfg or {}).get("terms") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def terms(config=None) -> list:
    return list(_all(config).keys())


def find_term(utterance, config=None):
    """认出问的哪个天气名词（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def explain(term, config=None) -> str:
    """某个天气名词的通俗解释。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(term or ""), str(term or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}"


def is_weather_term_query(utterance, config=None) -> bool:
    """是不是在问天气预报里的名词意思。"""
    u = str(utterance or "")
    if not find_term(u, config):
        return False
    return any(k in u for k in ("是什么", "啥意思", "什么意思", "怎么看", "多少算", "几级", "严重吗",
                                "怎么回事", "是啥", "咋看", "高吗", "好吗", "要紧吗"))


def count(config=None) -> int:
    return len(_all(config))
