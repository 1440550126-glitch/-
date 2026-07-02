"""手机帮手：老人最常被难住的那几件事——微信视频、发语音、发照片、调大字体、连WiFi。
一步步说清楚，慢慢来；实在不行，喊孩子搭把手。也顺带提一句防骗。

步骤尽量通用（各家手机略有差别）。纯逻辑、可单测。可在 config 加你这台手机的具体步骤。
"""

from __future__ import annotations

# 任务 → (触发词, 步骤)
_TASKS = [
    {"name": "微信视频通话", "keys": ["视频通话", "微信视频", "视频聊天", "怎么视频"],
     "steps": "打开微信，点开和对方的聊天框，点右下角的「＋」，选「视频通话」，等对方接就行。"},
    {"name": "发微信语音", "keys": ["发语音", "语音消息", "怎么发语音", "按住说话"],
     "steps": "打开和对方的聊天，按住下面「按住说话」那一条，对着手机说，说完松手就发出去了。"},
    {"name": "发照片", "keys": ["发照片", "发图片", "怎么发照片", "传照片"],
     "steps": "打开聊天，点「＋」，选「相册」，挑出要发的照片，再点「发送」。"},
    {"name": "微信收付款", "keys": ["微信付款", "微信收款", "怎么付钱", "扫码付", "收付款", "付款码"],
     "steps": "付钱：点「＋」或「收付款」，把那个条形码/二维码给收银员扫一下。"
              "收钱也在「收付款」里。切记：只在当面买东西时用，陌生人发来的码千万别扫、别付。"},
    {"name": "调大字体", "keys": ["字体太小", "字太小", "调大字", "字体大", "看不清字", "放大字"],
     "steps": "微信里：「我」→「设置」→「通用」→「字体大小」，往大拖。"
              "整个手机：「设置」→「显示」→「字体大小」，调大就清楚了。"},
    {"name": "连WiFi", "keys": ["连wifi", "连无线", "连网", "怎么上网", "连不上网", "wifi怎么连"],
     "steps": "「设置」→「WLAN / 无线局域网」→打开开关→选你家的网络名→输入密码→连上就有网了。"},
    {"name": "接打电话", "keys": ["怎么打电话", "怎么接电话", "拨电话", "接听"],
     "steps": "来电话时，绿色键是接、红色键是挂。打电话点拨号键，输号码，或在联系人里点名字再点拨号。"},
    {"name": "截图", "keys": ["截图", "截屏", "怎么截图", "保存屏幕"],
     "steps": "多数手机同时按住「电源键＋音量减键」一下就截屏了；有的能用三根手指往下滑。"},
    {"name": "找回密码", "keys": ["忘记密码", "密码忘了", "找回密码", "登不上", "登录不了"],
     "steps": "别急，更别把验证码告诉任何人。点登录页的「忘记密码」，按提示用手机号找回；"
              "实在弄不明白，等孩子来帮你，别在催促下乱操作。"},
    {"name": "清理内存", "keys": ["手机卡", "卡顿", "内存满", "清理手机", "手机慢"],
     "steps": "关掉一些后台不用的程序；微信里「我」→「设置」→「通用」→「存储空间」清一清缓存；"
              "实在卡，重启一下手机往往就顺了。"},
]


def _tasks(config) -> list:
    items = list(_TASKS)
    if isinstance(config, dict) and isinstance(config.get("phone_help"), list):
        for t in config["phone_help"]:
            if isinstance(t, dict) and t.get("name") and t.get("steps"):
                t.setdefault("keys", [t["name"]])
                items = [t] + items
    return items


def tasks(config=None) -> list:
    return [t["name"] for t in _tasks(config)]


def find_task(query, config=None) -> dict | None:
    u = str(query or "")
    best, blen = None, 0
    for t in _tasks(config):
        for k in t["keys"]:
            if k in u and len(k) > blen:
                best, blen = t, len(k)
    return best


def help_for(query, config=None) -> str:
    """这件事怎么操作。认不出返回空。"""
    t = find_task(query, config)
    if not t:
        return ""
    return f"{t['name']}：{t['steps']} 慢慢来，弄不明白随时喊我或喊孩子。"


def is_phone_help(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_task(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "不会", "教我", "教教", "弄不", "搞不",
                                "手机", "微信")) or "怎么" in u
