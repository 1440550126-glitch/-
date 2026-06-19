"""背诗：老人爱跟孙辈对诗——"床前明月光"接"疑是地上霜"，也能整首背一背。
一小撮耳熟能详的唐诗，可在 config/poetry.yaml 里加自己爱的。纯逻辑、可单测。
"""

from __future__ import annotations

_POEMS = {
    "静夜思": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
    "春晓": ["春眠不觉晓", "处处闻啼鸟", "夜来风雨声", "花落知多少"],
    "悯农": ["锄禾日当午", "汗滴禾下土", "谁知盘中餐", "粒粒皆辛苦"],
    "登鹳雀楼": ["白日依山尽", "黄河入海流", "欲穷千里目", "更上一层楼"],
    "咏鹅": ["鹅鹅鹅", "曲项向天歌", "白毛浮绿水", "红掌拨清波"],
    "草": ["离离原上草", "一岁一枯荣", "野火烧不尽", "春风吹又生"],
    "相思": ["红豆生南国", "春来发几枝", "愿君多采撷", "此物最相思"],
    "游子吟": ["慈母手中线", "游子身上衣", "临行密密缝", "意恐迟迟归"],
}


def collect(config=None) -> dict:
    """内置诗 + config/poetry.yaml 的 poems（{标题: [句, 句…]}）。"""
    out = dict(_POEMS)
    add = (config or {}).get("poems") if isinstance(config, dict) else None
    if isinstance(add, dict):
        for title, lines in add.items():
            ls = [str(x).strip() for x in (lines or []) if str(x).strip()]
            if title and ls:
                out[str(title).strip()] = ls
    return out


def _clean(line):
    return str(line or "").strip().strip("。，,.！!？?、 ")


def next_line(line, poems=None):
    """对上某句，接它的下一句；接不上返回空。"""
    target = _clean(line)
    if not target:
        return ""
    for _title, lines in (poems or _POEMS).items():
        for i, ln in enumerate(lines[:-1]):
            cl = _clean(ln)
            if cl and (cl == target or (len(cl) >= 3 and cl in target)):  # 上句在问话里
                return lines[i + 1]
    return ""


def find_title(query, poems=None):
    q = str(query or "")
    for title in (poems or _POEMS):
        if title and title in q:
            return title
    return None


def recite(title, poems=None) -> str:
    lines = (poems or _POEMS).get(title)
    return f"《{title}》——" + "，".join(lines) + "。" if lines else ""


def titles(poems=None) -> list:
    return list((poems or _POEMS).keys())


def is_poetry(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("下一句", "接下一句", "背首", "背一首", "背个", "背诗",
                                "念首", "念个", "对诗", "接诗", "下半句", "整首", "后一句"))
