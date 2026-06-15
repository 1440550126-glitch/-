"""记忆图谱测试。可直接运行：python tests/test_graph.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.authority import Authority  # noqa: E402
from dsoul.graph import MemoryGraph, build_memory_graph  # noqa: E402
from dsoul.memory import Memory  # noqa: E402


def test_graph_core_queries():
    g = MemoryGraph()
    g.add_relation("张明", "小婷", "老婆")
    g.add_memory("张明升职了特别开心", [("张明", "person"), ("升职", "topic")])
    g.add_memory("小婷和张明一起去看电影", [("张明", "person"), ("小婷", "person"), ("电影", "topic")])
    # 共现成边
    assert dict(g.neighbors("张明")).get("小婷")
    assert dict(g.neighbors("张明")).get("升职")
    # 实体检索
    assert "张明升职了特别开心" in g.about("升职")
    # 中心度：张明最核心
    assert g.central(1)[0][0] == "张明"
    # 两人之间有共享记忆
    bt = g.between("张明", "小婷")
    assert bt["edge"] >= 1 and bt["shared"]


def test_build_from_memory_and_authority():
    rel = {"people": [
        {"name": "张明", "relation": "本人", "trust": "owner"},
        {"name": "小婷", "relation": "老婆", "trust": "family"},
    ]}
    m = Memory(tempfile.mktemp(suffix=".json"))
    m.add("小婷陪张明去医院复查", source="x")
    g = build_memory_graph(m, Authority(rel))
    assert "小婷" in g.nodes() and "张明" in g.nodes()
    assert g.meta["小婷"].get("relation") == "老婆"          # 关系边带标签
    assert dict(g.neighbors("张明")).get("小婷")              # 主人—小婷 有连接


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ graph: all tests passed")
