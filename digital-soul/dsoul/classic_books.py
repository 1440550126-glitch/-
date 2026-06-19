"""古典名著：四大名著讲讲谁写的、谁是主角、讲了啥——给孙辈开开眼，自己也温故。
"四大名著是哪四部""西游记主要人物有谁"，张口就答。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 书名 → (作者/朝代, 主要人物, 一句故事梗概)
_BOOKS = {
    "红楼梦": ("清·曹雪芹", "贾宝玉、林黛玉、薛宝钗、王熙凤",
               "借贾府由盛而衰，写一段宝黛爱情悲剧和封建大家庭的兴亡，‘金陵十二钗’各有命运。"),
    "西游记": ("明·吴承恩", "唐僧、孙悟空、猪八戒、沙僧",
               "师徒四人西天取经，历经九九八十一难、降妖除魔，终成正果。"),
    "水浒传": ("明·施耐庵", "宋江、林冲、武松、鲁智深、李逵",
               "一百单八将被‘逼上梁山’，聚义替天行道，终归招安、走向悲剧。"),
    "三国演义": ("明·罗贯中", "刘备、曹操、孙权、诸葛亮、关羽、张飞",
                 "魏蜀吴三国争雄，桃园结义、赤壁之战、六出祁山，‘分久必合、合久必分’。"),
    "聊斋志异": ("清·蒲松龄", "各路书生与狐仙鬼怪",
                 "以鬼狐花妖的故事讽喻人间世态，写尽人情冷暖。"),
    "儒林外史": ("清·吴敬梓", "范进、严监生、王冕",
                 "讽刺科举制度下读书人的众生相，‘范进中举’最为人知。"),
    "封神演义": ("明·许仲琳", "姜子牙、哪吒、纣王、妲己",
                 "武王伐纣、神仙斗法，姜子牙封神，神话色彩浓厚。"),
    "镜花缘": ("清·李汝珍", "唐敖、林之洋、多九公",
               "游历海外诸国奇闻，借奇幻寄寓对世道与女子才情的思考。"),
}

_ALIAS = {"石头记": "红楼梦", "红楼": "红楼梦", "西游": "西游记", "水浒": "水浒传",
          "三国": "三国演义", "聊斋": "聊斋志异"}

_FOUR = ("红楼梦", "西游记", "水浒传", "三国演义")


def books() -> list:
    return list(_BOOKS)


def four_classics() -> str:
    return "四大名著是：" + "、".join(f"《{b}》" for b in _FOUR) + "。"


def find_book(query) -> str:
    u = str(query or "")
    best, blen = "", 0
    for b in _BOOKS:
        if b in u and len(b) > blen:
            best, blen = b, len(b)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen:
            best, blen = real, len(a)
    return best


def about(book) -> str:
    b = book if book in _BOOKS else find_book(book)
    row = _BOOKS.get(b)
    if not row:
        return ""
    author, chars, plot = row
    return f"《{b}》（{author}）：{plot} 主要人物有{chars}。"


def characters(book) -> str:
    b = book if book in _BOOKS else find_book(book)
    row = _BOOKS.get(b)
    return f"《{b}》的主要人物：{row[1]}。" if row else ""


def is_book_query(utterance) -> bool:
    u = str(utterance or "")
    if "四大名著" in u:
        return True
    if find_book(u) and any(k in u for k in ("谁写的", "作者", "主要人物", "讲什么", "讲的啥",
                                             "讲了啥", "讲讲", "里有谁", "主角", "是谁写",
                                             "内容", "简介", "梗概")):
        return True
    return False
