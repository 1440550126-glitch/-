"""手机帮手测试。可直接运行：python tests/test_phone_help.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.phone_help import (  # noqa: E402
    find_task,
    help_for,
    is_phone_help,
    tasks,
)


def test_tasks_cover():
    ts = tasks()
    assert any("视频" in t for t in ts)
    assert any("字体" in t for t in ts)
    assert any("WiFi" in t or "wifi" in t.lower() for t in ts)


def test_help_for_video():
    s = help_for("微信视频怎么打")
    assert "视频通话" in s and "对方" in s


def test_help_for_fontsize():
    s = help_for("手机字太小怎么调大")
    assert "字体" in s and ("设置" in s or "微信" in s)


def test_help_for_wifi():
    s = help_for("怎么连wifi")
    assert "密码" in s


def test_help_unknown_empty():
    assert help_for("怎么造火箭") == ""


def test_find_task_longest():
    t = find_task("发语音怎么发")
    assert t and "语音" in t["name"]


def test_is_phone_help():
    assert is_phone_help("微信视频怎么打")
    assert is_phone_help("字太小怎么调大")
    assert is_phone_help("教我连wifi")
    assert not is_phone_help("今天几号")
    assert not is_phone_help("视频真好看")            # 没有"怎么/教我/手机"等求助意图


def test_help_has_reassurance():
    s = help_for("怎么发照片")
    assert "慢慢来" in s or "喊" in s


def test_config_add():
    cfg = {"phone_help": [{"name": "扫健康码", "keys": ["健康码", "扫码进门"],
                           "steps": "打开支付宝/微信，搜'健康码'，亮出来给人扫。"}]}
    assert "扫健康码" in tasks(cfg)
    assert "健康码" in help_for("健康码怎么弄", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ phone_help: all tests passed")
