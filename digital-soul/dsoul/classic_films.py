"""怀旧影视：陪长辈唠唠老电影、老电视剧——那些一提名字就来劲、能聊半宿的经典。
不是追新片，是翻出一代人的共同记忆：打仗的、唱戏的、名著改编的、老动画……
按类型/心情推几部，或顺着提到的片名搭句话。纯数据 + 纯逻辑、可单测。

收的都是公认的经典老片，年代标个大概；想看新片请用别的渠道，这里专管"忆当年"。
"""

from __future__ import annotations

# 类型 -> [(片名, 年代/类型注, 一句话)]
_FILMS = {
    "革命战争": [
        ("地道战", "1965 电影", "村里挖地道打鬼子，机智又解气，几代人都看过。"),
        ("地雷战", "1962 电影", "土法埋雷斗敌人，'不见鬼子不挂弦'。"),
        ("英雄儿女", "1964 电影", "'为了胜利，向我开炮！'——王成那句喊得人热血。"),
        ("小兵张嘎", "1963 电影", "机灵的嘎子，孩子最爱看的小英雄。"),
        ("闪闪的红星", "1974 电影", "潘冬子和那首《红星照我去战斗》。"),
        ("上甘岭", "1956 电影", "一条坑道守阵地，《我的祖国》就出自这儿。"),
    ],
    "戏曲歌舞": [
        ("刘三姐", "1960 电影", "广西山歌对得又俏又甜，'多谢了'唱遍大江南北。"),
        ("五朵金花", "1959 电影", "大理风光 + 白族姑娘，找金花找出一段佳话。"),
        ("阿诗玛", "1964 电影", "撒尼族的传说，画面和歌都美。"),
        ("天仙配", "1955 黄梅戏", "'树上的鸟儿成双对'，七仙女和董永。"),
    ],
    "名著改编": [
        ("红楼梦", "1987 电视剧", "陈晓旭的林黛玉，公认的经典，主题曲一响就入戏。"),
        ("西游记", "1986 电视剧", "六小龄童的美猴王，暑假一遍遍重播也看不腻。"),
        ("三国演义", "1994 电视剧", "鲍国安的曹操、唐国强的诸葛亮，气派。"),
        ("水浒传", "1998 电视剧", "'大河向东流'，一百单八将。"),
    ],
    "武侠功夫": [
        ("少林寺", "1982 电影", "李连杰一战成名，'牧羊曲'悠扬，掀起功夫热。"),
        ("射雕英雄传", "1983 电视剧", "翁美玲的黄蓉，'靖哥哥蓉儿'一代人的回忆。"),
        ("霍元甲", "1983 电视剧", "'万里长城永不倒'，唱得人精神。"),
        ("白蛇传", "1992 电视剧", "赵雅芝的白娘子，断桥相会美极了。"),
    ],
    "喜剧搞笑": [
        ("大话西游", "1995 电影", "周星驰，'曾经有一份真挚的感情'，笑着笑着就哭了。"),
        ("甲方乙方", "1997 电影", "葛优冯小刚贺岁片开山，'1997 年过去了，我很怀念它'。"),
        ("我爱我家", "1993 情景剧", "傅明老人一家，中国情景喜剧的祖师爷。"),
        ("举起手来", "2003 电影", "郭达潘长江，老人孩子都笑得动。"),
    ],
    "家庭情感": [
        ("渴望", "1990 电视剧", "刘慧芳，万人空巷，'好人一生平安'。"),
        ("庐山恋", "1980 电影", "改革开放初的纯爱，庐山美景定情。"),
        ("牧马人", "1982 电影", "'老许，你要老婆不要'，质朴动人。"),
        ("人到中年", "1982 电影", "潘虹演的眼科大夫，那一代知识分子的酸甜。"),
    ],
    "国产动画": [
        ("大闹天宫", "1961/64 动画", "美猴王大闹天宫，国漫巅峰，色彩惊艳。"),
        ("哪吒闹海", "1979 动画", "'我把这条命还给你'，悲壮又好看。"),
        ("黑猫警长", "1984 动画", "'请看下集'，几代小朋友的警长。"),
        ("葫芦兄弟", "1986 动画", "七个葫芦娃斗蛇精，剪纸风一绝。"),
        ("天书奇谭", "1983 动画", "蛋生与三只狐狸，想象力飞起。"),
        ("阿凡提", "1980 动画", "倒骑毛驴的智者，专治财主。"),
    ],
}

_ALIAS = {
    "革命战争": "革命战争", "战争": "革命战争", "打仗": "革命战争", "打鬼子": "革命战争",
    "抗战": "革命战争", "红色": "革命战争", "老战斗": "革命战争",
    "戏曲歌舞": "戏曲歌舞", "戏曲": "戏曲歌舞", "唱戏": "戏曲歌舞", "黄梅戏": "戏曲歌舞",
    "山歌": "戏曲歌舞", "歌舞": "戏曲歌舞",
    "名著改编": "名著改编", "名著": "名著改编", "四大名著": "名著改编", "红楼": "名著改编",
    "西游": "名著改编", "三国": "名著改编", "水浒": "名著改编",
    "武侠功夫": "武侠功夫", "武侠": "武侠功夫", "功夫": "武侠功夫", "武打": "武侠功夫", "金庸": "武侠功夫",
    "喜剧搞笑": "喜剧搞笑", "喜剧": "喜剧搞笑", "搞笑": "喜剧搞笑", "逗乐": "喜剧搞笑", "贺岁": "喜剧搞笑",
    "家庭情感": "家庭情感", "情感": "家庭情感", "言情": "家庭情感", "家庭": "家庭情感", "爱情": "家庭情感",
    "国产动画": "国产动画", "动画": "国产动画", "动画片": "国产动画", "卡通": "国产动画", "美术片": "国产动画",
}


def _all(config=None) -> dict:
    d = {k: list(v) for k, v in _FILMS.items()}
    cfg = (config or {}).get("classic_films") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        for cat, lst in cfg.items():
            bucket = d.setdefault(str(cat), [])
            for f in (lst or []):
                if isinstance(f, (list, tuple)) and f:
                    bucket.append((str(f[0]), str(f[1]) if len(f) > 1 else "",
                                   str(f[2]) if len(f) > 2 else ""))
                elif isinstance(f, dict) and f.get("title"):
                    bucket.append((str(f["title"]), str(f.get("when", "")), str(f.get("note", ""))))
    return d


def categories(config=None) -> list:
    return list(_all(config).keys())


def find_category(utterance, config=None):
    """从话里听出类型（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for cat in _all(config):
        if cat in u:
            return cat
    return None


def films_in(category, config=None) -> list:
    cat = _ALIAS.get(str(category or ""), str(category or ""))
    return list(_all(config).get(cat, []))


def find_title(utterance, config=None):
    """提到了某部片名就把它揪出来，返回 (片名, 年代, 一句话)；没有返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for lst in _all(config).values():
        for f in lst:
            if f[0] in u and len(f[0]) > best_len:
                best, best_len = f, len(f[0])
    return best


def _fmt(f) -> str:
    title, when, note = f
    head = f"《{title}》" + (f"（{when}）" if when else "")
    return f"{head}{('：' + note) if note else ''}"


def recommend(category=None, seed="", config=None, n=3) -> str:
    """推几部：给了类型就推该类型的，否则跨类型挑几部。"""
    if category:
        pool = films_in(category, config)
    else:
        pool = [f for lst in _all(config).values() for f in lst]
    if not pool:
        return ""
    s = len(str(seed))
    picks = [pool[(s + i) % len(pool)] for i in range(min(max(1, int(n)), len(pool)))]
    # 去重保序
    seen, uniq = set(), []
    for p in picks:
        if p[0] not in seen:
            seen.add(p[0])
            uniq.append(p)
    lead = f"想看{category}的话，" if category else "随便给你翻几部老片，"
    return lead + "；".join(_fmt(f) for f in uniq) + "。哪部有印象，咱就聊聊那会儿。"


def count(config=None) -> int:
    return sum(len(v) for v in _all(config).values())


def is_film_query(utterance, config=None) -> bool:
    """是不是在聊/求老电影老电视剧。"""
    u = str(utterance or "")
    kind = any(k in u for k in ("老电影", "老电视剧", "老片", "经典电影", "经典老片",
                                "怀旧影视", "动画片", "老动画", "美术片"))
    if kind:
        return True
    # "有什么电影/电视剧推荐" + 看/推荐/经典
    if any(k in u for k in ("电影", "电视剧", "片子")) and \
       any(k in u for k in ("推荐", "看点啥", "看什么", "有啥", "有什么", "经典", "怀旧", "重温")):
        return True
    # 直接报了类型 + 想看
    if find_category(u, config) and any(k in u for k in ("推荐", "看", "重温", "怀旧", "有啥", "有什么")):
        return True
    return False
