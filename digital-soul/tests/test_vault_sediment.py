"""知识沉淀测试。可直接运行：python tests/test_vault_sediment.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul import vault_sediment as vs  # noqa: E402
from dsoul.knowledge_vault import Vault  # noqa: E402

N = "2026-06-25"


def _vault():
    return Vault(tempfile.mkdtemp(prefix="sed_"))


def test_split_concept():
    assert vs.split_concept("川菜（四川菜）：麻辣鲜香。")[0] == "川菜"
    assert vs.split_concept("清一色：整副牌全是同一花色。")[0] == "清一色"
    assert vs.split_concept("饺子的讲究：形似元宝。")[0] == "饺子"      # 削掉"的讲究"
    assert vs.split_concept("哈哈那必须的，张明，我记得……") is None     # 兜底闲聊不算
    assert vs.split_concept("「锲而不舍」——荀子") is None              # 没"："不算
    assert vs.split_concept("净：花脸。") is None                       # 单字标题太薄，跳过


def test_candidates_filters_by_route():
    entries = [
        {"reply": "川菜：麻辣鲜香。", "executed": "cuisines"},
        {"reply": "清一色：同花色。", "executed": "mahjong"},
        {"reply": "别慌，我在。", "executed": "emergency"},        # 非知识路由
        {"reply": "今天天气不错。", "executed": "smalltalk"},      # 非知识路由
    ]
    c = vs.candidates(entries)
    titles = [x["title"] for x in c]
    assert "川菜" in titles and "清一色" in titles and len(c) == 2


def test_sediment_creates_and_dedups():
    v = _vault()
    entries = [
        {"reply": "川菜（四川菜）：麻辣鲜香，名菜回锅肉。", "executed": "cuisines", "speaker": "张明"},
        {"reply": "清一色：整副牌全是同一花色。", "executed": "mahjong", "speaker": "张明"},
        {"reply": "川菜（四川菜）：麻辣鲜香，名菜回锅肉。", "executed": "cuisines", "speaker": "张明"},  # 重复
    ]
    rep = vs.sediment(v, entries, now=N)
    assert set(rep["created"]) == {"川菜", "清一色"}        # 重复只建一次
    assert v.has("川菜") and "#cuisines" in v.read("川菜")
    assert "沉淀" in (v.note("川菜")["frontmatter"].get("source") or "")


def test_sediment_appends_new_info_only():
    v = _vault()
    vs.sediment(v, [{"reply": "川菜：麻辣鲜香。", "executed": "cuisines"}], now=N)
    # 完全相同 → 不追加
    rep_same = vs.sediment(v, [{"reply": "川菜：麻辣鲜香。", "executed": "cuisines"}], now="2026-06-26")
    assert rep_same["appended"] == []
    # 有新内容 → 追加补记
    rep_new = vs.sediment(v, [{"reply": "川菜：还分上河帮下河帮小河帮。", "executed": "cuisines"}],
                          now="2026-06-27")
    assert "川菜" in rep_new["appended"]
    assert "## 补记 2026-06-27" in v.read("川菜")


def test_sediment_writes_daily_note():
    v = _vault()
    rep = vs.sediment(v, [{"reply": "川菜：麻辣鲜香。", "executed": "cuisines"}], now=N)
    daily = (v.root / "日记" / f"{N}.md")
    assert daily.exists() and "今天沉淀了" in daily.read_text(encoding="utf-8")
    assert "[[川菜]]" in daily.read_text(encoding="utf-8")


def test_sediment_empty_when_nothing():
    v = _vault()
    rep = vs.sediment(v, [{"reply": "别慌，我在。", "executed": "emergency"}], now=N)
    assert rep["touched"] == [] and rep["candidates"] == 0


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ vault_sediment: all tests passed")
