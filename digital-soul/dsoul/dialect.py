"""乡音：让分身会说几句家乡话——那一声"要得""中""老灵额"，比标准普通话更像本人。
有了嗓音，再带上乡音，听着才是记忆里那个人的腔调。

只做**轻量、安全**的方言点缀：换几个常用词、缀个语气词、答一句"行不行"，
不做整句硬翻（那样容易翻拧、反而不像）。纯逻辑、可单测。
配 config/identity.yaml 的 `dialect:`（如"四川"），或随口"用东北话说一句"。
"""

from __future__ import annotations

# 各地常用词/答语/语气词（取广为人知、不易出错的那几个）
_PRESETS = {
    "四川": {
        "hello": "吃了没哟？", "yes": "要得", "no": "莫得", "good": "巴适得很",
        "thanks": "多谢哈", "particles": ["嘛", "哈", "哦", "噻"],
        "words": {"什么": "啥子", "没有": "没得", "知道": "晓得", "怎么": "咋个",
                  "舒服": "巴适", "厉害": "凶", "玩": "耍"},
    },
    "东北": {
        "hello": "干哈呢？", "yes": "中", "no": "不行", "good": "老好了",
        "thanks": "谢谢哈", "particles": ["啊", "呗", "哈", "呐"],
        "words": {"什么": "啥", "干什么": "嘎哈", "很": "贼", "怎么办": "咋整",
                  "聊天": "唠嗑", "喜欢": "稀罕", "知道": "知道"},
    },
    "北京": {
        "hello": "吃了吗您内？", "yes": "成", "no": "不成", "good": "倍儿棒",
        "thanks": "劳驾了", "particles": ["啊", "嘞", "哈"],
        "words": {"很": "倍儿", "什么": "嘛", "知道": "知道", "厉害": "局气",
                  "聊天": "侃", "走": "颠儿"},
    },
    "陕西": {
        "hello": "吃咧没？", "yes": "嫽", "no": "不成", "good": "嫽扎咧",
        "thanks": "麻烦咧", "particles": ["撒", "么", "咧"],
        "words": {"什么": "啥", "不知道": "知不道", "聊天": "谝", "好": "嫽",
                  "怎么": "咋"},
    },
    "河南": {
        "hello": "吃了冇？", "yes": "中", "no": "不中", "good": "可得劲",
        "thanks": "谢谢嘞", "particles": ["嘞", "啊", "哩"],
        "words": {"干什么": "弄啥", "什么": "啥", "舒服": "得劲", "怎么": "咋",
                  "好": "中"},
    },
    "山东": {
        "hello": "吃了吗？", "yes": "好来", "no": "不沾", "good": "杠赛来",
        "thanks": "谢谢哈", "particles": ["来", "哈", "啊"],
        "words": {"什么": "么", "昨天": "夜来", "好极了": "杠赛来", "怎么": "咋",
                  "知道": "知道"},
    },
    "广东": {
        "hello": "食咗饭未？", "yes": "系", "no": "唔系", "good": "几好",
        "thanks": "唔该", "particles": ["啦", "嘅", "喎", "咩"],
        "words": {"你": "你", "什么": "乜嘢", "知道": "知道", "好看": "靓",
                  "没有": "冇", "是": "系"},
    },
    "上海": {
        "hello": "饭吃过伐？", "yes": "好额", "no": "勿来", "good": "老灵额",
        "thanks": "谢谢侬", "particles": ["额", "伐", "呀"],
        "words": {"你": "侬", "我们": "阿拉", "什么": "啥", "知道": "晓得",
                  "很好": "老灵额", "厉害": "结棍"},
    },
}

# 别名 → 标准地名
_ALIAS = {
    "川": "四川", "成都": "四川", "重庆": "四川", "巴蜀": "四川",
    "东北话": "东北", "辽": "东北", "黑": "东北", "吉": "东北",
    "京": "北京", "老北京": "北京",
    "秦": "陕西", "西安": "陕西",
    "豫": "河南", "郑州": "河南",
    "鲁": "山东", "济南": "山东",
    "粤": "广东", "广州": "广东", "香港": "广东", "广东话": "广东", "白话": "广东",
    "沪": "上海", "吴": "上海", "上海话": "上海",
}


def regions() -> list:
    """会说的乡音。"""
    return list(_PRESETS.keys())


def normalize_region(region) -> str:
    """把"川/成都/广东话"等都归到标准地名；认不出返回空。"""
    r = str(region or "").strip().replace("话", "").replace("方言", "")
    if r in _PRESETS:
        return r
    for k, v in _ALIAS.items():
        if k.replace("话", "") == r or r in (k, v):
            return v
    return ""


def preset(region) -> dict:
    return dict(_PRESETS.get(normalize_region(region), {}))


def say_in(region, concept) -> str:
    """用某地乡音说一个常用意（hello/yes/no/good/thanks）。没有返回空。"""
    return preset(region).get(concept, "")


def swap_words(text, region) -> str:
    """把句中几个常用词换成乡音说法（轻量、安全）。"""
    p = preset(region)
    out = str(text or "")
    # 长词先换，避免"干什么"被"什么"先吃掉
    for std in sorted(p.get("words", {}), key=len, reverse=True):
        out = out.replace(std, p["words"][std])
    return out


def season(text, region, level=1, seed="") -> str:
    """给一句话点上乡音：换几个词 +（可选）缀个语气词。level=0 不点缀。"""
    r = normalize_region(region)
    if not r or level <= 0:
        return str(text or "")
    out = swap_words(text, r)
    parts = preset(r).get("particles", [])
    if level >= 2 and parts and out:
        tail = out.rstrip()
        # 句尾标点前插一个语气词，像随口那么一缀
        if tail and tail[-1] in "。.!！?？":
            out = tail[:-1] + parts[len(str(seed)) % len(parts)] + tail[-1]
        else:
            out = tail + parts[len(str(seed)) % len(parts)]
    return out


def demo(region) -> str:
    """秀一句这地方的乡音（招呼 + 一句应答）。"""
    r = normalize_region(region)
    if not r:
        return ""
    p = _PRESETS[r]
    return f"{p['hello']}……（{r}话）应一声就是“{p['yes']}”，夸一句“{p['good']}”。"


def region_in(utterance, extra=None) -> str:
    """从话里认出提到的地方话（含别名）。认不出返回空。"""
    u = str(utterance or "")
    for r in list(_PRESETS) + list(_ALIAS) + list(extra or []):
        if r in u:
            return normalize_region(r) or (r if r in _PRESETS else "")
    return ""


def is_dialect_request(utterance) -> bool:
    u = utterance or ""
    if any(k in u for k in ("家乡话", "方言", "土话", "乡音", "老家话")):
        return True
    # 提到某地，且像是"想听这地方的话"："用四川话说""来段东北话""说点上海话"
    r = region_in(u)
    if r:
        if (r + "话") in u:
            return True
        if any(k in u for k in ("话说", "话讲", "话怎么", "怎么说", "说一句", "说句",
                                "说点", "讲一句", "讲句", "来一句", "来段", "来点",
                                "整一句", "秀一句", "飙一句", "讲段")):
            return True
    return False
