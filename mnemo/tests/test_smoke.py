"""全链路冒烟测试：记忆 / 画像 / 工具循环 / 调度 / 技能 / 离线 provider。

零依赖运行：  python -m unittest discover -s tests   或   python tests/test_smoke.py
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnemo.agent import Agent, parse_tool_call          # noqa: E402
from mnemo.config import load_config                     # noqa: E402
from mnemo.daemon import compute_next, parse_schedule    # noqa: E402
from mnemo.memory import Memory, _tokens                 # noqa: E402
from mnemo.providers import build_provider               # noqa: E402
from mnemo.providers.base import Message, Provider       # noqa: E402
from mnemo.providers.offline import OfflineProvider      # noqa: E402
from mnemo.skills import SkillRegistry                   # noqa: E402
from mnemo.skills import distill_from_trace              # noqa: E402
from mnemo.tools import ToolContext, build_default_registry  # noqa: E402


class FakeProvider(Provider):
    """按脚本逐条返回，用于驱动并验证 Agent 工具循环。"""
    name = "fake"

    def __init__(self, scripted):
        super().__init__()
        self.scripted = list(scripted)

    def chat(self, messages, **kw):
        return self.scripted.pop(0) if self.scripted else "（无更多脚本）"


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(Path(self.tmp.name) / "m.db")

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_fact_and_recall(self):
        self.mem.add_fact("用户在做一个终端 AI 助理项目 Mnemo", importance=4)
        self.mem.add_fact("用户喜欢喝美式咖啡", kind="preference", importance=4)
        hits = self.mem.recall("咖啡")
        self.assertTrue(any("咖啡" in h["text"] for h in hits))

    def test_observe_learns_profile(self):
        self.mem.observe("你好，我叫小明，我喜欢爬山", "你好小明！")
        self.assertEqual(self.mem.get_profile("name"), "小明")
        summary = self.mem.profile_summary()
        self.assertIn("小明", summary)
        self.assertEqual(int(self.mem.get_profile("interactions")), 1)

    def test_tokens_cjk(self):
        toks = _tokens("终端 AI 助理")
        self.assertIn("ai", toks)


class TestAgentLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_tool_then_final(self):
        prov = FakeProvider([
            '好的，先看下时间\n```tool\n{"name": "now", "args": {}}\n```',
            "现在帮你记住了。",
        ])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        events = []
        out = agent.run("你好，我叫小红", on_event=lambda k, d: events.append((k, d)))
        self.assertEqual(out, "现在帮你记住了。")
        self.assertTrue(any(k == "tool" and d["name"] == "now" for k, d in events))
        self.assertEqual(self.mem.get_profile("name"), "小红")

    def test_remember_tool_writes_memory(self):
        prov = FakeProvider([
            '```tool\n{"name":"remember","args":{"text":"用户的生日是 6 月 16 日","importance":5}}\n```',
            "已记住你的生日。",
        ])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        agent.run("记一下我的生日")
        self.assertTrue(any("生日" in f["text"] for f in self.mem.all_facts()))


class FakeEmbedProvider(Provider):
    name = "fakeembed"

    def chat(self, messages, **kw):
        return "ok"

    def embed(self, texts):
        return [[float(t.count("猫")), float(t.count("狗"))] for t in texts]


class TestProactiveMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(Path(self.tmp.name) / "m.db")

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_semantic_recall(self):
        self.mem.add_fact("我家有一只橘猫")
        self.mem.add_fact("邻居养了大狗")
        self.assertEqual(self.mem.embed_backfill(FakeEmbedProvider()), 2)
        qvec = FakeEmbedProvider().embed(["猫"])[0]
        hits = self.mem.recall("猫", query_vec=qvec)
        self.assertTrue(any("猫" in h["text"] for h in hits))
        self.assertFalse(any("狗" in h["text"] for h in hits))

    def test_consolidate_merges_near_dup(self):
        self.mem.add_fact("用户喜欢喝美式咖啡", importance=3)
        self.mem.add_fact("用户喜欢喝美式咖啡哦", importance=2)
        res = self.mem.consolidate()
        self.assertGreaterEqual(res["merged"], 1)

    def test_consolidate_forgets_stale(self):
        fid = self.mem.add_fact("一条不重要的旧信息", importance=1)
        self.mem.db.execute("UPDATE facts SET created_at=? WHERE id=?",
                            (time.time() - 60 * 86400, fid))
        self.mem.db.commit()
        res = self.mem.consolidate(max_age_days=30)
        self.assertGreaterEqual(res["forgotten"], 1)

    def test_reminders(self):
        rid = self.mem.add_reminder("买牛奶", time.time() - 10)
        self.assertTrue(any(r["id"] == rid for r in self.mem.due_reminders()))
        self.mem.mark_reminder_done(rid)
        self.assertEqual(self.mem.due_reminders(), [])

    def test_parse_when(self):
        from mnemo.memory import parse_when
        self.assertEqual(parse_when("in 1h", now=1000.0), 1000.0 + 3600)
        self.assertIsNone(parse_when("看不懂的时间"))


class TestEvolveAndDelegate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_delegate_runs_subagent(self):
        prov = FakeProvider(["子任务完成：答案是 42"])  # 子 Agent 直接给最终答案
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        ctx = ToolContext(memory=self.mem, config=self.cfg, agent=agent)
        out = self.tools.run("delegate", {"role": "研究员", "task": "算一下"}, ctx)
        self.assertIn("研究员", out)
        self.assertIn("42", out)

    def test_delegate_depth_guard(self):
        prov = FakeProvider(["x"])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg, _depth=2)
        ctx = ToolContext(memory=self.mem, config=self.cfg, agent=agent)
        out = self.tools.run("delegate", {"task": "x"}, ctx)
        self.assertIn("深度", out)

    def test_distill_heuristic(self):
        trace = {"input": "列出目录并统计文件数",
                 "steps": [{"tool": "list_dir", "args": {"path": "."}, "result": "a\nb"}],
                 "final": "共 2 个文件"}
        text = distill_from_trace(trace, OfflineProvider(), "list-and-count")
        self.assertTrue(text.strip().startswith("---"))
        self.assertIn("list-and-count", text)
        self.assertIn("list_dir", text)
        s = self.skills.learn(name="list-and-count", text=text)
        self.assertIsNotNone(self.skills.get("list-and-count"))
        self.assertTrue(s.path.exists())


class TestParsing(unittest.TestCase):
    def test_parse_nested_args(self):
        txt = '```tool\n{"name":"write_file","args":{"path":"a.txt","content":"x{y}z"}}\n```'
        name, args = parse_tool_call(txt)
        self.assertEqual(name, "write_file")
        self.assertEqual(args["path"], "a.txt")

    def test_parse_none_when_plain(self):
        self.assertIsNone(parse_tool_call("这是一句普通回答，没有工具。"))

    def test_parse_bare_json(self):
        name, args = parse_tool_call('{"name": "now", "args": {}}')
        self.assertEqual(name, "now")


class TestSchedule(unittest.TestCase):
    def test_interval(self):
        self.assertEqual(parse_schedule("every 5m"), ("interval", 300))
        self.assertEqual(parse_schedule("2h"), ("interval", 7200))
        self.assertEqual(compute_next("every 10s", 1000.0), 1010.0)

    def test_daily_and_startup(self):
        self.assertEqual(parse_schedule("@daily 09:30"), ("daily", (9, 30)))
        self.assertEqual(parse_schedule("@startup")[0], "startup")
        self.assertIsNone(compute_next("@startup", 1000.0))


class TestProvidersAndSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_auto_falls_back_offline(self):
        # 测试环境无 Key、无 Ollama，auto 应回退到 offline
        prov = build_provider(self.cfg)
        self.assertTrue(prov.available())

    def test_offline_echo(self):
        out = OfflineProvider().chat([Message("user", "echo 你好")])
        self.assertEqual(out, "你好")

    def test_offline_remember_emits_tool(self):
        out = OfflineProvider().chat([Message("user", "记住 我喜欢猫")])
        name, args = parse_tool_call(out)
        self.assertEqual(name, "remember")

    def test_builtin_skills_loaded(self):
        sk = SkillRegistry(self.cfg)
        names = [s.name for s in sk.list()]
        self.assertIn("daily-briefing", names)


class TestTools(unittest.TestCase):
    def test_read_write_roundtrip(self):
        from mnemo.tools import ToolContext
        tmp = tempfile.TemporaryDirectory()
        reg = build_default_registry()
        ctx = ToolContext(cwd=tmp.name, config=load_config(tmp.name))
        reg.run("write_file", {"path": "hello.txt", "content": "你好 Mnemo"}, ctx)
        out = reg.run("read_file", {"path": "hello.txt"}, ctx)
        self.assertIn("你好 Mnemo", out)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
