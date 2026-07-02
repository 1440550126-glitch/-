"""蒙学：教孙辈念几句老祖宗的开蒙书——三字经、弟子规、百家姓、千字文，
再背背九九乘法口诀。爷爷奶奶膝头那点启蒙，一辈辈传下来。

只收公有领域的经典开篇；算术留给日常问答，这儿只管"背口诀"。纯逻辑、可单测。
"""

from __future__ import annotations

# 开蒙经典的开篇（公有领域古籍）
_CLASSICS = {
    "三字经": "人之初，性本善。性相近，习相远。苟不教，性乃迁。教之道，贵以专。",
    "弟子规": "弟子规，圣人训。首孝悌，次谨信。泛爱众，而亲仁。有余力，则学文。",
    "百家姓": "赵钱孙李，周吴郑王。冯陈褚卫，蒋沈韩杨。朱秦尤许，何吕施张。",
    "千字文": "天地玄黄，宇宙洪荒。日月盈昃，辰宿列张。寒来暑往，秋收冬藏。",
}

_DIGITS = "零一二三四五六七八九"


def classics() -> list:
    return list(_CLASSICS.keys())


def find_classic(utterance) -> str:
    u = str(utterance or "")
    for name in _CLASSICS:
        if name in u:
            return name
    return ""


def recite(name) -> str:
    """念一段开蒙经典的开篇。认不出返回空。"""
    n = find_classic(name) or str(name or "").strip()
    body = _CLASSICS.get(n, "")
    return f"《{n}》开篇：{body}" if body else ""


def _num_cn(n) -> str:
    """口诀里的数：10→一十、12→十二、21→二十一、49→四十九。"""
    if n < 10:
        return _DIGITS[n]
    if n == 10:
        return "一十"
    if n < 20:
        return "十" + (_DIGITS[n - 10] if n % 10 else "")
    return _DIGITS[n // 10] + "十" + (_DIGITS[n % 10] if n % 10 else "")


def pair_rhyme(a, b) -> str:
    """单句口诀：pair_rhyme(7,3)→'三七二十一'，pair_rhyme(2,3)→'二三得六'。"""
    lo, hi = sorted((int(a), int(b)))
    if not (1 <= lo and hi <= 9):
        return ""
    p = lo * hi
    head = _DIGITS[lo] + _DIGITS[hi]
    return head + ("得" if p < 10 else "") + _num_cn(p)


def times_row(n) -> str:
    """某一列的口诀：times_row(7)→'一七得七，二七十四，…，七七四十九。'"""
    n = int(n)
    if not 1 <= n <= 9:
        return ""
    return "，".join(pair_rhyme(j, n) for j in range(1, n + 1)) + "。"


def times_table() -> str:
    """整张九九乘法表（按列，逐行）。"""
    return "\n".join(times_row(n) for n in range(1, 10))


def wants_classic(utterance) -> bool:
    u = str(utterance or "")
    if not find_classic(u):
        return False
    return any(k in u for k in ("背", "念", "读", "教", "给我", "来一段", "来段",
                                "是什么", "是啥", "怎么", "咋", "听", "讲", "开篇",
                                "开头", "几句")) or u.strip() in _CLASSICS


def wants_times_table(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("乘法口诀", "九九表", "九九乘法", "背乘法", "乘法表", "九九歌")):
        return True
    # "三的乘法口诀 / 七的口诀"
    if "口诀" in u and any(d in u for d in _DIGITS[1:]):
        return True
    return False


def times_query_row(utterance):
    """从'三的乘法口诀'里取出是哪一列；取不到返回 None。"""
    u = str(utterance or "")
    for i in range(9, 0, -1):
        if _DIGITS[i] in u or str(i) in u:
            return i
    return None
