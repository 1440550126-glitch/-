"""神态：把此刻的心情挂在脸上——眉眼、嘴角，再配一束相称的光。
有身体的动作（embodiment）、有声气（vocalics），再加一张会变的脸，才是个活物。

给带屏幕/灯带的机器人和网页状态页用：情绪 → 表情描述 + 灯色 + 一个表情符。
纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

# 情绪 → 神态（眉/眼/嘴）+ 灯色(名,十六进制) + 表情符
_FACES = {
    "喜": {"brow": "眉梢舒展", "eyes": "眼睛弯弯发亮", "mouth": "嘴角上扬",
           "color": ("暖黄", "#FFD66B"), "emoji": "😊"},
    "乐": {"brow": "眉飞色舞", "eyes": "眼睛眯成缝", "mouth": "咧嘴大笑",
           "color": ("明黄", "#FFE680"), "emoji": "😄"},
    "哀": {"brow": "眉头微蹙下垂", "eyes": "眼神黯淡有些湿", "mouth": "嘴角抿着下撇",
           "color": ("沉蓝", "#6B8CBE"), "emoji": "😔"},
    "惧": {"brow": "眉头紧锁", "eyes": "眼睛睁大警觉", "mouth": "嘴唇微张",
           "color": ("冷青", "#7FB3C9"), "emoji": "😟"},
    "怒": {"brow": "眉头拧紧", "eyes": "双眼圆睁", "mouth": "嘴抿成一条线",
           "color": ("暗红", "#C9544B"), "emoji": "😠"},
    "爱": {"brow": "眉眼柔和", "eyes": "眼里含着温柔", "mouth": "温温的浅笑",
           "color": ("柔粉", "#F3A6B5"), "emoji": "🥰"},
    "欲": {"brow": "眉梢微挑", "eyes": "眼神专注发亮", "mouth": "抿嘴带着期待",
           "color": ("暖橙", "#F0A85A"), "emoji": "😋"},
    "中": {"brow": "眉目平和", "eyes": "目光温和", "mouth": "神情自然",
           "color": ("柔白", "#EDEDED"), "emoji": "🙂"},
}

_DEFAULT = "中"


def _key(emotion) -> str:
    e = str(emotion or "").strip()
    return e if e in _FACES else _DEFAULT


def face_for(emotion) -> dict:
    """此刻的神态（含眉眼嘴/灯色/表情符）。认不出按平和。"""
    return dict(_FACES[_key(emotion)])


def describe_face(emotion) -> str:
    """一句话神情，给网页/日志看：'眼睛弯弯发亮、嘴角上扬（暖黄的光）'。"""
    f = _FACES[_key(emotion)]
    return f"{f['eyes']}、{f['mouth']}（{f['color'][0]}的光）"


def led_color(emotion):
    """灯色 (名称, 十六进制)，给灯带/氛围灯。"""
    return _FACES[_key(emotion)]["color"]


def emoji_for(emotion) -> str:
    return _FACES[_key(emotion)]["emoji"]


def emotions() -> list:
    return [e for e in _FACES if e != _DEFAULT]
