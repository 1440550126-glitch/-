"""口腔护理：牙好胃口才好。怎么把牙刷干净、假牙怎么养、牙龈出血牙疼咋回事——
上了年纪护好这口牙，能多享好些年口福。纯逻辑、可单测。
和"导诊"(triage 看牙挂口腔科)接着用，这里讲日常护理。

⚠️ 牙疼、牙龈老出血、牙松、口腔溃疡两周不好，别拖，看牙科/口腔科。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "刷牙": ("早晚各刷一次、每次 2～3 分钟；用软毛牙刷、含氟牙膏；'巴氏刷牙法'——刷毛斜 45 度对着牙龈沟、"
           "小幅来回颤动，里里外外、咬合面都刷到，别使蛮力横着拉。",
           "牙刷 3 个月换一支、刷毛炸开就换；舌苔也轻轻刷刷。"),
    "牙线": ("光刷牙刷不到牙缝，每天用一次牙线或牙缝刷，把缝里的食物残渣、牙菌斑带出来。",
           "牙缝大的用牙缝刷更顺手；别用牙签使劲剔，伤牙龈。"),
    "假牙护理": ("活动假牙每餐后取下冲洗、用软牙刷蘸牙膏（别用太硬的）刷干净；晚上摘下泡在凉水或假牙清洁液里，"
              "别戴着睡；别用开水烫（会变形）。",
              "戴着硌、松了、磨破口子，找牙医调，别凑合戴出溃疡。"),
    "牙龈出血": ("刷牙时牙龈出血，多半是牙龈发炎、有牙结石——好好刷牙 + 用牙线 + 洗牙，多能好转。",
              "总出血、红肿、口臭，去看牙周；别因为出血就不敢刷，越不刷越糟。"),
    "洗牙": ("半年到一年洗一次牙，去掉刷不掉的牙结石，防牙龈炎、牙周病。",
           "洗完觉得牙缝变大、有点酸，是结石没了露出来的、过几天就好，不是把牙'洗松'了。"),
    "牙疼": ("牙疼多是蛀牙、牙髓发炎，自己好不了、还会越来越重——尽早看牙科补牙或治疗，别拖成大窟窿。",
           "疼起来先别吃太烫太凉太甜的；实在疼可暂吃止痛药，但治本还得看牙。"),
    "口腔溃疡": ("嘴里溃疡多数 1～2 周自己好；这阵子别吃辣、烫、硬的，补点维生素、多喝水、好好休息。",
              "⚠️ 同一处溃疡超过 2 周不好、或边缘硬、反复长，去口腔科查查，别大意。"),
    "口臭": ("多数口臭出在口腔：好好刷牙刷舌、用牙线、洗牙、治牙周病，多能改善。",
           "口腔弄干净了还持续口臭，可能和肠胃、鼻咽有关，查一查。"),
    "牙齿松动缺牙": ("老人牙松多是牙周病闹的，早看牙周还能保住；牙缺了别空着——会影响咀嚼、邻牙也跟着歪，"
                "及时镶牙或种牙补上。",
                "牙好才嚼得动、吃得香、营养够；这口牙值得花心思。"),
}

_ALIAS = {
    "刷牙": "刷牙", "怎么刷牙": "刷牙", "刷牙方法": "刷牙", "巴氏刷牙": "刷牙",
    "怎么刷": "刷牙", "刷干净": "刷牙", "牙刷": "刷牙",
    "牙线": "牙线", "牙缝刷": "牙线", "牙缝": "牙线",
    "假牙护理": "假牙护理", "假牙": "假牙护理", "活动假牙": "假牙护理", "义齿": "假牙护理",
    "牙龈出血": "牙龈出血", "牙龈": "牙龈出血", "刷牙出血": "牙龈出血", "牙龈肿": "牙龈出血",
    "洗牙": "洗牙", "洁牙": "洗牙", "牙结石": "洗牙", "牙石": "洗牙",
    "牙疼": "牙疼", "牙痛": "牙疼", "蛀牙": "牙疼", "龋齿": "牙疼",
    "口腔溃疡": "口腔溃疡", "口疮": "口腔溃疡", "嘴里溃疡": "口腔溃疡",
    "口臭": "口臭", "嘴臭": "口臭", "口气大": "口臭",
    "牙齿松动缺牙": "牙齿松动缺牙", "牙松": "牙齿松动缺牙", "牙松动": "牙齿松动缺牙", "缺牙": "牙齿松动缺牙",
    "掉牙": "牙齿松动缺牙", "镶牙": "牙齿松动缺牙", "种牙": "牙齿松动缺牙",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("dental_care") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类口腔护理（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类的做法 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def is_dental_query(utterance, config=None) -> bool:
    """是不是在问口腔/牙齿护理。"""
    u = str(utterance or "")
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "正确", "方法", "怎么办", "怎么养", "要紧吗", "咋回事",
                                "是什么", "怎么回事", "好不好", "该", "护理", "保护", "会不会", "吗"))


def count(config=None) -> int:
    return len(_all(config))
