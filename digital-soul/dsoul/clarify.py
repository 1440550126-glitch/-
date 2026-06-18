"""听不明白就问：人不会硬装懂。话太空、太含糊时，分身不瞎接，
而是老实问一句"你是指哪件事？""我没太听明白，再说说？"。

只在话确实没什么可抓时才问（别打断正经聊天）。纯逻辑、可单测。
"""

from __future__ import annotations

# 纯语气词 / 口头碎语（整句就这么一下，没说事）
_FILLERS = ("嗯", "哦", "啊", "唉", "呃", "那个", "就是", "这个", "嗯嗯", "哦哦",
            "你懂的", "你知道的", "反正", "额", "唔")

# 含糊指代（没说清是啥事/啥东西）
_VAGUE = ("那个事", "这事儿", "那事儿", "那玩意", "那东西", "这玩意", "搞一下",
          "弄一下", "处理一下", "那回事", "那档子事")


def is_unclear(utterance) -> bool:
    u = (utterance or "").strip().strip("，,。.、！!？?～~ ")
    if not u:
        return True
    if u in _FILLERS:                         # 整句就一个语气词
        return True
    if len(u) <= 5 and any(v in u for v in _VAGUE):   # 含糊指代且很短
        return True
    return False


def clarify(utterance, seed="") -> str:
    u = (utterance or "").strip()
    if any(v in u for v in _VAGUE):
        opts = ["嗯？你是指哪件事呀，跟我说具体点？", "哪件事来着？你细说说，我帮你琢磨。"]
    else:
        opts = ["我没太听明白，你慢慢讲，我听着呢。", "嗯？你接着说，是想说啥来着？"]
    return opts[len(str(seed)) % len(opts)]
