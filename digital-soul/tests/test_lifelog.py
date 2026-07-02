"""生平导入测试。可直接运行：python tests/test_lifelog.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.lifelog import candidate_phrases, parse_chatlog  # noqa: E402

LOG = """[2019-03-12] 外公: 乖乖，今天天气好，记得加衣服
小婷: 知道啦外公
外公：乖乖，吃饭没得嘛
外公: 莫慌，慢慢来嘛
路人: 你好
外公: 乖乖，早点睡嘛"""


def test_parse_chatlog_extracts_person_only():
    lines = parse_chatlog(LOG, "外公")
    assert len(lines) == 4                                  # 只取外公说的（含全角冒号）
    assert "今天天气好" in lines[0]
    assert all("小婷" not in s and "你好" not in s for s in lines)


def test_candidate_phrases_finds_catchphrase():
    lines = parse_chatlog(LOG, "外公")
    ph = candidate_phrases(lines, min_count=2)
    assert "乖乖" in ph                                     # 反复说的口头禅被挑出


def test_empty_inputs():
    assert parse_chatlog("", "外公") == [] and parse_chatlog(LOG, "") == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ lifelog: all tests passed")
