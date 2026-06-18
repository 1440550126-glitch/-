"""全链路冒烟测试：记忆 / 画像 / 工具循环 / 调度 / 技能 / 离线 provider。

零依赖运行：  python -m unittest discover -s tests   或   python tests/test_smoke.py
"""
import json as _json
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnemo.agent import Agent, parse_tool_call          # noqa: E402
from mnemo.config import load_config                     # noqa: E402
from mnemo.daemon import compute_next, parse_schedule    # noqa: E402
from mnemo.memory import Memory, _tokens                 # noqa: E402
from mnemo.providers import build_provider               # noqa: E402
from mnemo.providers.base import Message, Provider       # noqa: E402
from mnemo.providers.offline import OfflineProvider      # noqa: E402
from mnemo.providers.openai import OpenAIProvider         # noqa: E402
from mnemo.providers.anthropic import AnthropicProvider   # noqa: E402
import mnemo.providers.openai as openai_mod               # noqa: E402
import mnemo.providers.anthropic as anthropic_mod         # noqa: E402
from mnemo.plugins import PluginManager                  # noqa: E402
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

    def test_observe_extracts_new_patterns(self):
        self.mem.observe("我的生日是 5 月 20 日", "好的")
        self.mem.observe("我住在杭州", "记住了")
        self.mem.observe("我的目标是今年跑完马拉松", "加油")
        self.mem.observe("我女儿叫朵朵", "真可爱")
        facts = [f["text"] for f in self.mem.all_facts()]
        self.assertTrue(any("生日" in f for f in facts))
        self.assertTrue(any("杭州" in f for f in facts))
        self.assertTrue(any("马拉松" in f for f in facts))
        self.assertTrue(any("女儿" in f and "朵朵" in f for f in facts))
        prof = self.mem.profile_summary()
        self.assertIn("马拉松", prof)             # goal 进画像

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

    def test_audit_logged(self):
        prov = FakeProvider(['```tool\n{"name":"now","args":{}}\n```', "现在是…"])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        agent.run("几点了")
        audit = self.cfg.home / "audit.log"
        self.assertTrue(audit.exists())
        self.assertIn("now", audit.read_text(encoding="utf-8"))

    def test_deny_policy_blocks_tool(self):
        ctx = ToolContext(config=self.cfg, deny=("run_shell",))
        out = self.tools.run("run_shell", {"command": "echo hi"}, ctx)
        self.assertIn("禁用", out)

    def test_remember_tool_writes_memory(self):
        prov = FakeProvider([
            '```tool\n{"name":"remember","args":{"text":"用户的生日是 6 月 16 日","importance":5}}\n```',
            "已记住你的生日。",
        ])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        agent.run("记一下我的生日")
        self.assertTrue(any("生日" in f["text"] for f in self.mem.all_facts()))


class TestStreaming(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_offline_stream_reconstructs_chat(self):
        prov = OfflineProvider()
        msgs = [Message("user", "echo: 你好世界")]
        streamed = "".join(prov.stream(msgs))
        self.assertEqual(streamed, prov.chat(msgs))
        self.assertEqual(streamed, "你好世界")

    def test_base_default_stream_yields_full(self):
        prov = FakeProvider(["完整回答"])
        self.assertEqual("".join(prov.stream([Message("user", "x")])), "完整回答")

    def test_on_token_streams_final_answer(self):
        prov = FakeProvider(["这是最终答案"])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        got = []
        out = agent.run("问题", on_token=got.append)
        self.assertEqual(out, "这是最终答案")
        self.assertEqual("".join(got), "这是最终答案")

    def test_on_token_does_not_leak_tool_json(self):
        prov = FakeProvider([
            '```tool\n{"name":"now","args":{}}\n```',  # 工具步：不应回显
            "现在几点已查到。",                          # 最终答案：应回显
        ])
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        got = []
        out = agent.run("几点了", on_token=got.append)
        self.assertEqual(out, "现在几点已查到。")
        joined = "".join(got)
        self.assertEqual(joined, "现在几点已查到。")
        self.assertNotIn("{", joined)      # 工具调用 JSON 未泄漏给用户


class FakeEmbedProvider(Provider):
    name = "fakeembed"

    def chat(self, messages, **kw):
        return "ok"

    def embed(self, texts):
        return [[float(t.count("猫")), float(t.count("狗"))] for t in texts]


class TestRecurringReminders(unittest.TestCase):
    def test_repeat_seconds(self):
        from mnemo.memory import repeat_seconds
        self.assertEqual(repeat_seconds("daily"), 86400)
        self.assertEqual(repeat_seconds("weekly"), 604800)
        self.assertEqual(repeat_seconds("every 3d"), 3 * 86400)
        self.assertIsNone(repeat_seconds(None))
        self.assertIsNone(repeat_seconds("nonsense"))

    def test_daemon_reschedules_repeat(self):
        from mnemo.daemon import Scheduler, TaskStore
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        mem = Memory(cfg.db_path)
        past = time.time() - 100
        rid = mem.add_reminder("吃药", past, repeat="daily")
        agent = Agent(FakeProvider(["ok"]), build_default_registry(),
                      mem, SkillRegistry(cfg), cfg)
        sched = Scheduler(agent, TaskStore(cfg.db_path), log=lambda *a: None)
        sched._maintenance(time.time())
        # 周期提醒应被改期到未来，而非标记完成
        pend = mem.pending_reminders()
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]["id"], rid)
        self.assertGreater(pend[0]["remind_at"], time.time())
        mem.close()
        tmp.cleanup()


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

    def test_ann_candidates(self):
        self.mem.add_fact("我家有一只橘猫")
        self.mem.add_fact("邻居养了大狗")
        self.mem.embed_backfill(FakeEmbedProvider())
        qvec = FakeEmbedProvider().embed(["猫"])[0]
        cands = self.mem.ann_candidates(qvec)
        cat = [f["id"] for f in self.mem.all_facts() if "猫" in f["text"]][0]
        dog = [f["id"] for f in self.mem.all_facts() if "狗" in f["text"]][0]
        self.assertIn(cat, cands)
        self.assertNotIn(dog, cands)

    def test_graph_and_html(self):
        self.mem.add_fact("用户在做终端 AI 助理 Mnemo")
        self.mem.add_fact("用户给 Mnemo 加了永久记忆功能")
        g = self.mem.graph()
        self.assertGreaterEqual(len(g["nodes"]), 2)
        from mnemo.viz import render_graph_html
        html = render_graph_html(g)
        self.assertIn("<!doctype", html)
        self.assertIn("Mnemo", html)

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


class FakeNativeProvider(Provider):
    name = "fakenative"

    def __init__(self, scripted):
        super().__init__()
        self.scripted = list(scripted)
        self.seen = []

    def supports_tools(self):
        return True

    def chat_tools(self, messages, tool_specs, **kw):
        self.seen.append(list(messages))
        return self.scripted.pop(0)

    def chat(self, messages, **kw):
        return "n/a"


class TestNativeTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_native_loop_roundtrips_tool_results(self):
        prov = FakeNativeProvider([
            {"text": "先看时间", "tool_calls": [{"id": "c1", "name": "now", "args": {}}]},
            {"text": "好的，记住了", "tool_calls": []},
        ])
        self.cfg.set("native_tools", True)
        agent = Agent(prov, self.tools, self.mem, self.skills, self.cfg)
        out = agent.run("你好，我叫阿强")
        self.assertEqual(out, "好的，记住了")
        self.assertEqual(self.mem.get_profile("name"), "阿强")
        second = prov.seen[1]
        self.assertTrue(any(getattr(m, "tool_call_id", None) == "c1" for m in second))

    def test_openai_translate(self):
        msgs = [Message("system", "sys"), Message("user", "hi"),
                Message("assistant", "", tool_calls=[{"id": "c1", "name": "now", "args": {}}]),
                Message("tool", "2026", name="now", tool_call_id="c1")]
        out = OpenAIProvider._to_native(msgs)
        self.assertEqual(out[2]["tool_calls"][0]["id"], "c1")
        self.assertEqual(out[3]["role"], "tool")
        self.assertEqual(out[3]["tool_call_id"], "c1")

    def test_openai_chat_tools_parse(self):
        prov = OpenAIProvider(api_key="x")
        orig = openai_mod.http_post_json
        openai_mod.http_post_json = lambda url, payload, headers=None, timeout=120: {
            "choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "now", "arguments": "{}"}}]}}]}
        try:
            res = prov.chat_tools([Message("user", "几点")],
                                  [{"name": "now", "description": "时间", "parameters": {}}])
        finally:
            openai_mod.http_post_json = orig
        self.assertEqual(res["tool_calls"][0]["name"], "now")

    def test_anthropic_translate(self):
        sys, conv = AnthropicProvider._to_native([
            Message("system", "S"), Message("user", "u"),
            Message("assistant", "", tool_calls=[{"id": "t1", "name": "now", "args": {}}]),
            Message("tool", "R", tool_call_id="t1")])
        self.assertEqual(sys, "S")
        self.assertEqual(conv[1]["content"][0]["type"], "tool_use")
        self.assertEqual(conv[2]["content"][0]["type"], "tool_result")


class TestGemini(unittest.TestCase):
    def test_to_contents_roles(self):
        from mnemo.providers.gemini import GeminiProvider
        sysinstr, contents = GeminiProvider._to_contents([
            Message("system", "S"), Message("user", "hi"),
            Message("assistant", "yo"), Message("tool", "R", name="now")])
        self.assertEqual(sysinstr["parts"][0]["text"], "S")
        self.assertEqual(contents[0]["role"], "user")
        self.assertEqual(contents[1]["role"], "model")
        self.assertIn("工具 now 返回", contents[2]["parts"][0]["text"])

    def test_chat_parses_and_usage(self):
        import mnemo.providers.gemini as gemini_mod
        prov = gemini_mod.GeminiProvider(api_key="x", model="gemini-2.0-flash")
        orig = gemini_mod.http_post_json
        gemini_mod.http_post_json = lambda url, payload, headers=None, timeout=120, retries=2: {
            "candidates": [{"content": {"parts": [{"text": "你好世界"}]}}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 4}}
        try:
            out = prov.chat([Message("user", "hi")])
        finally:
            gemini_mod.http_post_json = orig
        self.assertEqual(out, "你好世界")
        self.assertEqual(prov.last_usage, {"in": 12, "out": 4})

    def test_chat_tools_parses_functioncall(self):
        import mnemo.providers.gemini as gemini_mod
        prov = gemini_mod.GeminiProvider(api_key="x")
        orig = gemini_mod.http_post_json
        gemini_mod.http_post_json = lambda url, payload, headers=None, timeout=120, retries=2: {
            "candidates": [{"content": {"parts": [
                {"functionCall": {"name": "now", "args": {}}}]}}]}
        try:
            res = prov.chat_tools([Message("user", "几点")],
                                  [{"name": "now", "description": "时间", "parameters": {}}])
        finally:
            gemini_mod.http_post_json = orig
        self.assertEqual(res["tool_calls"][0]["name"], "now")

    def test_registered(self):
        from mnemo.providers import AUTO_ORDER, REGISTRY
        self.assertIn("gemini", REGISTRY)
        self.assertIn("gemini", AUTO_ORDER)


class TestMultimodalVoice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_view_image_offline_graceful(self):
        agent = Agent(OfflineProvider(), self.tools, self.mem, self.skills, self.cfg)
        ctx = ToolContext(agent=agent, config=self.cfg, cwd=".")
        out = self.tools.run("view_image", {"path": "nope.png"}, ctx)
        self.assertIn("不支持视觉", out)

    def test_openai_vision_parse(self):
        prov = OpenAIProvider(api_key="x")
        img = Path(self.tmp.name) / "a.png"
        img.write_bytes(b"\x89PNG-fake-bytes")
        orig = openai_mod.http_post_json
        openai_mod.http_post_json = lambda url, payload, headers=None, timeout=120: {
            "choices": [{"message": {"content": "一只橘猫"}}]}
        try:
            out = prov.vision(str(img), "这是什么")
        finally:
            openai_mod.http_post_json = orig
        self.assertEqual(out, "一只橘猫")

    def test_speak_graceful(self):
        out = self.tools.run("speak", {"text": "你好"}, ToolContext())
        self.assertIsInstance(out, str)

    def test_transcribe_missing_file(self):
        out = self.tools.run("transcribe", {"path": "/no/such.wav"}, ToolContext())
        self.assertIn("不存在", out)


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


class TestSyncAndMarket(unittest.TestCase):
    def test_sync_roundtrip_encrypted(self):
        from mnemo import sync
        src = tempfile.TemporaryDirectory()
        dst = tempfile.TemporaryDirectory()
        m = Memory(Path(src.name) / "mnemo.db")
        m.add_fact("跨设备永久记忆测试", importance=5)
        m.close()
        bundle = Path(src.name) / "backup.mnemo"
        sync.export_bundle(Path(src.name), bundle, passphrase="pw123")
        sync.import_bundle(bundle, Path(dst.name), passphrase="pw123")
        m2 = Memory(Path(dst.name) / "mnemo.db")
        self.assertTrue(any("跨设备" in f["text"] for f in m2.all_facts()))
        m2.close()
        src.cleanup()
        dst.cleanup()

    def test_sync_wrong_passphrase(self):
        from mnemo import sync
        tmp = tempfile.TemporaryDirectory()
        Memory(Path(tmp.name) / "mnemo.db").close()
        bundle = Path(tmp.name) / "b.mnemo"
        sync.export_bundle(Path(tmp.name), bundle, passphrase="right")
        with self.assertRaises(ValueError):
            sync.import_bundle(bundle, Path(tmp.name) / "out", passphrase="wrong")
        tmp.cleanup()

    def test_market_install_skill_from_file(self):
        from mnemo.market import install, search
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        skills = SkillRegistry(cfg)
        plugins = PluginManager(cfg, build_default_registry(), skills)
        md = Path(tmp.name) / "src.md"
        md.write_text("---\nname: x\ndescription: 复盘技能\n---\n正文", encoding="utf-8")
        reg = {"skills": [{"name": "market-skill", "description": "复盘技能", "file": str(md)}],
               "plugins": []}
        self.assertEqual(len(search(reg, "复盘")["skills"]), 1)
        what = install("market-skill", reg, skills, plugins)
        self.assertEqual(what, "skill:market-skill")
        self.assertIsNotNone(skills.get("market-skill"))
        tmp.cleanup()


class TestExamplePlugins(unittest.TestCase):
    def test_echo_provider_plugin(self):
        import shutil
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        src = Path(__file__).resolve().parents[1] / "examples" / "plugins" / "echo-provider"
        shutil.copytree(src, Path(cfg.plugins_dir) / "echo-provider")
        reg = build_default_registry()
        PluginManager(cfg, reg, SkillRegistry(cfg)).load_all()
        # 插件注入的工具可用
        self.assertIn("shout", reg.names())
        self.assertEqual(reg.run("shout", {"text": "hi"}, ToolContext()), "HI!!!")
        # 插件注册的自定义 Provider 可被构建
        from mnemo.providers import REGISTRY, build_provider
        self.assertIn("myecho", REGISTRY)
        cfg.set("provider", "myecho")
        prov = build_provider(cfg)
        self.assertEqual(prov.name, "myecho")
        tmp.cleanup()


class TestSandboxMediaVoice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.tools = build_default_registry()

    def tearDown(self):
        self.tmp.cleanup()

    def test_shell_runs_without_sandbox(self):
        ctx = ToolContext(config=self.cfg, cwd=".")
        out = self.tools.run("run_shell", {"command": "echo hello123"}, ctx)
        self.assertIn("hello123", out)

    def test_sandbox_refuses_when_engine_missing(self):
        import shutil
        if shutil.which("docker"):
            self.skipTest("docker present")
        self.cfg.set("sandbox.engine", "docker")
        ctx = ToolContext(config=self.cfg, cwd=".")
        out = self.tools.run("run_shell", {"command": "echo hi"}, ctx)
        self.assertIn("沙箱不可用", out)

    def test_extract_frames_no_ffmpeg(self):
        import shutil
        from mnemo.media import extract_frames, is_video
        self.assertTrue(is_video("a.mp4"))
        self.assertFalse(is_video("a.png"))
        if shutil.which("ffmpeg"):
            self.skipTest("ffmpeg present")
        self.assertEqual(extract_frames("nope.mp4"), [])

    def test_voice_missing_is_list(self):
        from mnemo import voice
        self.assertIsInstance(voice.missing(), list)


class TestServe(unittest.TestCase):
    def test_health_and_chat(self):
        from mnemo.serve import make_handler
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        mem = Memory(cfg.db_path, check_same_thread=False)
        agent = Agent(FakeProvider(["你好，我记住了"]), build_default_registry(),
                      mem, SkillRegistry(cfg), cfg)
        app = types.SimpleNamespace(provider=agent.provider, memory=mem, agent=agent)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, threading.Lock(), None))
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            h = _json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=5).read())
            self.assertTrue(h["ok"])
            st = _json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/status", timeout=5).read())
            self.assertEqual(st["provider"], "fake")
            self.assertIn("memory", st)
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/chat",
                data=_json.dumps({"message": "你好我叫小测"}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            r = _json.loads(urllib.request.urlopen(req, timeout=5).read())
            self.assertEqual(r["reply"], "你好，我记住了")
            self.assertEqual(mem.get_profile("name"), "小测")
        finally:
            httpd.shutdown()
            mem.close()
            tmp.cleanup()

    def test_auth_blocks_without_token(self):
        from mnemo.serve import make_handler
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        mem = Memory(cfg.db_path, check_same_thread=False)
        agent = Agent(FakeProvider(["x"]), build_default_registry(), mem, SkillRegistry(cfg), cfg)
        app = types.SimpleNamespace(provider=agent.provider, memory=mem, agent=agent)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, threading.Lock(), "secret"))
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/profile", timeout=5)
            self.assertEqual(cm.exception.code, 401)
        finally:
            httpd.shutdown()
            mem.close()
            tmp.cleanup()


class TestMarketTrust(unittest.TestCase):
    def test_sign_verify_and_tamper(self):
        from mnemo import market
        reg = {"name": "r", "skills": [], "plugins": []}
        signed = market.sign_registry(reg, "k")
        self.assertTrue(market.verify_registry(signed, "k"))
        self.assertFalse(market.verify_registry(signed, "wrong"))
        signed["skills"].append({"name": "evil"})        # 篡改后签名失效
        self.assertFalse(market.verify_registry(signed, "k"))

    def test_install_sha256_mismatch(self):
        from mnemo import market
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        skills = SkillRegistry(cfg)
        plugins = PluginManager(cfg, build_default_registry(), skills)
        md = Path(tmp.name) / "s.md"
        md.write_text("---\nname: x\n---\nbody", encoding="utf-8")
        reg = {"skills": [{"name": "s", "file": str(md), "sha256": "deadbeef"}], "plugins": []}
        with self.assertRaises(ValueError):
            market.install("s", reg, skills, plugins)
        tmp.cleanup()

    def test_ratings(self):
        from mnemo import market
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        market.rate(str(cfg.db_path), "hello", 5, "great")
        market.rate(str(cfg.db_path), "hello", 3)
        s = market.ratings_summary(str(cfg.db_path))
        self.assertEqual(s["hello"]["count"], 2)
        self.assertEqual(s["hello"]["avg"], 4.0)
        tmp.cleanup()


class TestReviewFixes(unittest.TestCase):
    def test_save_excludes_env_secret(self):
        import os
        os.environ["OPENAI_API_KEY"] = "sk-secret-xyz"
        try:
            tmp = tempfile.TemporaryDirectory()
            cfg = load_config(tmp.name)
            self.assertEqual(cfg.get("providers.openai.api_key"), "sk-secret-xyz")
            cfg.set("temperature", 0.3)
            cfg.save()
            data = _json.loads(cfg.config_file.read_text(encoding="utf-8"))
            self.assertNotIn("api_key", data.get("providers", {}).get("openai", {}))
            self.assertEqual(data["temperature"], 0.3)
            tmp.cleanup()
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_anthropic_omits_temp_for_opus(self):
        captured = {}
        orig = anthropic_mod.http_post_json
        anthropic_mod.http_post_json = (lambda url, payload, headers=None, timeout=120:
                                        (captured.update(payload) or
                                         {"content": [{"type": "text", "text": "hi"}]}))
        try:
            AnthropicProvider(api_key="x", model="claude-opus-4-8").chat(
                [Message("user", "hi")], temperature=0.7)
            self.assertNotIn("temperature", captured)
            captured.clear()
            AnthropicProvider(api_key="x", model="claude-sonnet-4-6").chat(
                [Message("user", "hi")], temperature=0.7)
            self.assertIn("temperature", captured)
        finally:
            anthropic_mod.http_post_json = orig

    def test_sync_rejects_path_traversal(self):
        import io
        import tarfile
        from mnemo import sync
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo("../evil.txt"); info.size = 4
            tar.addfile(info, io.BytesIO(b"evil"))
        tmp = tempfile.TemporaryDirectory()
        bundle = Path(tmp.name) / "b.tgz"
        bundle.write_bytes(buf.getvalue())
        with self.assertRaises(ValueError):
            sync.import_bundle(bundle, Path(tmp.name) / "home")
        tmp.cleanup()

    def test_parse_when_invalid(self):
        from mnemo.memory import parse_when
        self.assertIsNone(parse_when("25:00"))
        self.assertIsNone(parse_when("2026-13-40 10:00"))

    def test_offline_remember_json_safe(self):
        from mnemo.agent import parse_tool_call
        out = OfflineProvider().chat([Message("user", "记住 路径 C:\\tmp 和\n第二行")])
        name, args = parse_tool_call(out)
        self.assertEqual(name, "remember")
        self.assertIn("C:\\tmp", args["text"])
        self.assertIn("第二行", args["text"])

    def test_plugin_name_traversal_rejected(self):
        from mnemo.plugins import _safe_plugin_name
        for bad in ["../evil", "/abs", "a/b", "..", "x\\y"]:
            with self.assertRaises(ValueError):
                _safe_plugin_name(bad)
        self.assertEqual(_safe_plugin_name("good"), "good")


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

    def test_search_files_tool(self):
        tmp = tempfile.TemporaryDirectory()
        reg = build_default_registry()
        ctx = ToolContext(cwd=tmp.name, config=load_config(tmp.name))
        reg.run("write_file", {"path": "a.py", "content": "def foo():\n    return 42\n"}, ctx)
        reg.run("write_file", {"path": "b.txt", "content": "no match here\n"}, ctx)
        out = reg.run("search_files", {"pattern": r"def \w+", "glob": "*.py"}, ctx)
        self.assertIn("a.py", out)
        self.assertIn("def foo", out)
        self.assertNotIn("b.txt", out)
        self.assertIn("无匹配", reg.run("search_files", {"pattern": "zzz_nope"}, ctx))
        tmp.cleanup()

    def test_edit_file_tool(self):
        tmp = tempfile.TemporaryDirectory()
        reg = build_default_registry()
        ctx = ToolContext(cwd=tmp.name, config=load_config(tmp.name))
        reg.run("write_file", {"path": "a.py", "content": "x = 1\ny = 2\n"}, ctx)
        out = reg.run("edit_file", {"path": "a.py", "old": "x = 1", "new": "x = 42"}, ctx)
        self.assertIn("已编辑", out)
        self.assertIn("x = 42", reg.run("read_file", {"path": "a.py"}, ctx))
        # 不唯一 → 报错
        reg.run("write_file", {"path": "b.txt", "content": "a a a"}, ctx)
        dup = reg.run("edit_file", {"path": "b.txt", "old": "a", "new": "z"}, ctx)
        self.assertIn("不唯一", dup)
        # all=true 全部替换
        ok = reg.run("edit_file", {"path": "b.txt", "old": "a", "new": "z", "all": True}, ctx)
        self.assertIn("3 处", ok)
        tmp.cleanup()

    def test_http_request_tool(self):
        import mnemo.tools as tools_mod

        class FakeResp:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n=None): return b'{"ok":true}'

        captured = {}

        def fake_open(req, timeout=0):
            captured["method"] = req.get_method()
            captured["data"] = req.data
            return FakeResp()

        orig = tools_mod.urllib.request.urlopen
        tools_mod.urllib.request.urlopen = fake_open
        try:
            reg = build_default_registry()
            out = reg.run("http_request",
                          {"url": "https://api.x/1", "method": "post", "body": {"a": 1}},
                          ToolContext())
        finally:
            tools_mod.urllib.request.urlopen = orig
        self.assertIn("201", out)
        self.assertIn("ok", out)
        self.assertEqual(captured["method"], "POST")
        self.assertIn(b'"a": 1', captured["data"])


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(Path(self.tmp.name) / "m.db")
        self.docs = Path(self.tmp.name) / "docs"
        self.docs.mkdir()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_chunk_text(self):
        from mnemo.ingest import chunk_text
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("一句话"), ["一句话"])
        # 段落聚合
        small = chunk_text("第一段。\n\n第二段。", max_chars=100)
        self.assertEqual(len(small), 1)
        # 超长段落硬切
        big = chunk_text("x" * 250, max_chars=100)
        self.assertEqual(len(big), 3)
        self.assertTrue(all(len(c) <= 100 for c in big))

    def test_ingest_dir_and_recall(self):
        from mnemo.ingest import ingest_path
        (self.docs / "a.md").write_text("# 火星\n火星是太阳系第四颗行星，表面呈红色。",
                                        encoding="utf-8")
        (self.docs / "b.txt").write_text("光合作用把二氧化碳和水转化为葡萄糖。",
                                         encoding="utf-8")
        (self.docs / "ignore.bin").write_text("二进制不该被读取", encoding="utf-8")
        res = ingest_path(self.mem, self.docs)
        self.assertEqual(res["files"], 2)            # .bin 被跳过
        self.assertGreaterEqual(res["chunks"], 2)
        kinds = {f["kind"] for f in self.mem.all_facts()}
        self.assertIn("knowledge", kinds)
        hits = self.mem.recall("火星 行星")
        self.assertTrue(any("火星" in h["text"] for h in hits))

    def test_ingest_url(self):
        import mnemo.ingest as ing
        orig = ing.fetch_url_text
        ing.fetch_url_text = lambda url, timeout=20: "火星是太阳系第四颗行星。" * 8
        try:
            res = ing.ingest_url(self.mem, "https://example.com/mars")
        finally:
            ing.fetch_url_text = orig
        self.assertEqual(res["files"], 1)
        self.assertGreaterEqual(res["chunks"], 1)
        self.assertTrue(any(f["source"] == "ingest:https://example.com/mars"
                            for f in self.mem.all_facts()))

    def test_ingest_is_idempotent(self):
        from mnemo.ingest import ingest_path
        (self.docs / "a.md").write_text("永久记忆是 Mnemo 的核心卖点。", encoding="utf-8")
        ingest_path(self.mem, self.docs)
        n1 = self.mem.stats()["facts"]
        ingest_path(self.mem, self.docs)             # 再次摄入相同内容
        n2 = self.mem.stats()["facts"]
        self.assertEqual(n1, n2)                      # UNIQUE 约束天然去重

    def test_knowledge_not_in_profile(self):
        from mnemo.ingest import ingest_path
        (self.docs / "a.md").write_text("某个无关的技术文档内容。", encoding="utf-8")
        self.mem.set_profile("name", "小明")
        ingest_path(self.mem, self.docs)
        prof = self.mem.profile_summary()
        self.assertIn("小明", prof)
        self.assertNotIn("技术文档", prof)            # 知识块不进画像


class TestMemoryManagement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(Path(self.tmp.name) / "m.db")

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_facts_by_filters(self):
        self.mem.add_fact("知识A", kind="knowledge", tags="火星", source="ingest:a.md")
        self.mem.add_fact("知识B", kind="knowledge", tags="地球", source="ingest:b.md")
        self.mem.add_fact("偏好C", kind="preference", source="user")
        self.assertEqual(len(self.mem.facts_by(kind="knowledge")), 2)
        self.assertEqual(len(self.mem.facts_by(tag="火星")), 1)
        self.assertEqual(len(self.mem.facts_by(source="ingest:")), 2)
        self.assertEqual(len(self.mem.facts_by(source="ingest:a")), 1)

    def test_forget_by_source(self):
        self.mem.add_fact("x1", source="ingest:notes/a.md")
        self.mem.add_fact("x2", source="ingest:notes/b.md")
        self.mem.add_fact("keep", source="user")
        n = self.mem.forget_by_source("ingest:")
        self.assertEqual(n, 2)
        self.assertEqual(self.mem.stats()["facts"], 1)

    def test_export_markdown(self):
        self.mem.set_profile("name", "小红")
        self.mem.add_fact("用户喜欢咖啡", kind="preference", importance=4)
        md = self.mem.export_markdown()
        self.assertIn("# Mnemo 记忆导出", md)
        self.assertIn("小红", md)
        self.assertIn("咖啡", md)

    def test_session_summary_roundtrip(self):
        for i in range(8):
            self.mem.add_episode("s1", f"问题{i}", f"回答{i}")
        summ = self.mem.summarize_session("s1", FakeProvider(["早前对话摘要X"]), keep_recent=4)
        self.assertEqual(summ, "早前对话摘要X")
        self.assertEqual(self.mem.get_session_summary("s1"), "早前对话摘要X")

    def test_summarize_too_short_returns_none(self):
        self.mem.add_episode("s2", "a", "b")
        self.assertIsNone(self.mem.summarize_session("s2", FakeProvider(["x"]), keep_recent=4))

    def test_search_episodes(self):
        self.mem.add_episode("s1", "我想学习冲浪", "冲浪很有趣")
        self.mem.add_episode("s1", "今天天气不错", "是的")
        hits = self.mem.search_episodes("冲浪")
        self.assertEqual(len(hits), 1)
        self.assertIn("冲浪", hits[0]["user"])

    def test_sessions_listing(self):
        self.mem.add_episode("s1", "你好", "嗨")
        self.mem.add_episode("s1", "再问", "再答")
        self.mem.add_episode("s2", "另一个会话", "ok")
        sess = {r["session"]: r["c"] for r in self.mem.sessions()}
        self.assertEqual(sess["s1"], 2)
        self.assertEqual(sess["s2"], 1)
        eps = self.mem.session_episodes("s1")
        self.assertEqual(len(eps), 2)
        self.assertEqual(eps[0]["user"], "你好")


class TestNotify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_channel_none(self):
        from mnemo.notify import notify
        self.cfg.set("notify.channel", "none")
        self.assertEqual(notify(self.cfg, "hi"), "none")

    def test_webhook_used_when_configured(self):
        import mnemo.notify as nt
        sent = {}

        def fake_post(url, title, message, timeout=10):
            sent["url"], sent["msg"] = url, message
            return True
        orig = nt.webhook
        nt.webhook = fake_post
        self.cfg.set("notify.channel", "webhook")
        self.cfg.set("notify.webhook", "http://example/hook")
        try:
            ch = nt.notify(self.cfg, "提醒你喝水", title="T")
        finally:
            nt.webhook = orig
        self.assertEqual(ch, "webhook")
        self.assertEqual(sent["url"], "http://example/hook")
        self.assertEqual(sent["msg"], "提醒你喝水")

    def test_email_channel_used_when_configured(self):
        import mnemo.notify as nt
        sent = {}

        def fake_email(cfg, title, message):
            sent["to"] = cfg.get("to"); sent["msg"] = message
            return True
        orig = nt.email
        nt.email = fake_email
        self.cfg.set("notify.channel", "email")
        self.cfg.set("notify.email", {"smtp_host": "smtp.x", "to": "me@x.com"})
        try:
            ch = nt.notify(self.cfg, "每日简报", title="T")
        finally:
            nt.email = orig
        self.assertEqual(ch, "email")
        self.assertEqual(sent["to"], "me@x.com")

    def test_stdout_fallback(self):
        from mnemo.notify import notify
        self.cfg.set("notify.channel", "webhook")   # 但未配 webhook → 回退
        self.cfg.set("notify.webhook", "")
        self.assertEqual(notify(self.cfg, "hi"), "stdout")

    def test_notify_tool(self):
        import mnemo.notify as nt
        tools = build_default_registry()
        orig = nt.desktop
        nt.desktop = lambda t, m: False             # 强制走 stdout
        try:
            out = tools.run("notify", {"message": "测试"}, ToolContext(config=self.cfg))
        finally:
            nt.desktop = orig
        self.assertIn("通知", out)


class TestCalcAndPersona(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_calc_arithmetic(self):
        ctx = ToolContext()
        self.assertEqual(self.tools.run("calc", {"expr": "(3+4)*2"}, ctx), "14")
        self.assertEqual(self.tools.run("calc", {"expr": "2**10"}, ctx), "1024")
        self.assertEqual(self.tools.run("calc", {"expr": "sqrt(16)"}, ctx), "4.0")

    def test_calc_rejects_code(self):
        ctx = ToolContext()
        out = self.tools.run("calc", {"expr": "__import__('os').system('echo hi')"}, ctx)
        self.assertIn("无法计算", out)

    def test_persona_switch_changes_prompt(self):
        self.cfg.set("personas", {"程序员": "你是资深工程师。说中文。"})
        self.cfg.set("persona_active", "程序员")
        agent = Agent(FakeProvider(["x"]), self.tools, self.mem, self.skills, self.cfg)
        self.assertIn("资深工程师", agent._system_prompt("hi"))
        # 切回默认
        self.cfg.set("persona_active", None)
        self.assertIn("Mnemo", agent._system_prompt("hi"))


class TestAwareness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_due_reminder_injected_into_prompt(self):
        self.mem.add_reminder("给妈妈打电话", time.time() - 60)   # 已逾期
        agent = Agent(FakeProvider(["ok"]), self.tools, self.mem, self.skills, self.cfg)
        sp = agent._system_prompt("你好")
        self.assertIn("给妈妈打电话", sp)
        self.assertIn("当前情境", sp)

    def test_session_summary_injected(self):
        self.mem.set_session_summary("s9", "早前聊过登山计划")
        agent = Agent(FakeProvider(["x"]), self.tools, self.mem, self.skills, self.cfg)
        sp = agent._system_prompt("你好", session="s9")
        self.assertIn("早前聊过登山计划", sp)

    def test_forget_tool(self):
        fid = self.mem.add_fact("一条会被删除的记忆")
        out = self.tools.run("forget", {"id": fid}, ToolContext(memory=self.mem))
        self.assertIn("已删除", out)
        self.assertFalse(any(f["id"] == fid for f in self.mem.all_facts()))

    def test_recall_tool_shows_ids(self):
        self.mem.add_fact("用户喜欢喝美式", importance=4)
        out = self.tools.run("recall", {"query": "美式"}, ToolContext(memory=self.mem))
        self.assertRegex(out, r"#\d+")


class TestHttpRetry(unittest.TestCase):
    def test_retries_transient_then_succeeds(self):
        import mnemo.providers.base as base_mod
        calls = {"n": 0}

        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"ok": true}'

        def flaky(req, timeout=0):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.URLError("temporary")
            return FakeResp()

        o_open, o_sleep = base_mod.urllib.request.urlopen, base_mod.time.sleep
        base_mod.urllib.request.urlopen = flaky
        base_mod.time.sleep = lambda s: None
        try:
            out = base_mod.http_post_json("http://x", {}, retries=3)
        finally:
            base_mod.urllib.request.urlopen = o_open
            base_mod.time.sleep = o_sleep
        self.assertEqual(out, {"ok": True})
        self.assertEqual(calls["n"], 3)

    def test_no_retry_on_client_error(self):
        import io
        import mnemo.providers.base as base_mod
        calls = {"n": 0}

        def client_err(req, timeout=0):
            calls["n"] += 1
            raise urllib.error.HTTPError("http://x", 400, "Bad", {}, io.BytesIO(b"bad"))

        o_open, o_sleep = base_mod.urllib.request.urlopen, base_mod.time.sleep
        base_mod.urllib.request.urlopen = client_err
        base_mod.time.sleep = lambda s: None
        try:
            with self.assertRaises(base_mod.ProviderError):
                base_mod.http_post_json("http://x", {}, retries=3)
        finally:
            base_mod.urllib.request.urlopen = o_open
            base_mod.time.sleep = o_sleep
        self.assertEqual(calls["n"], 1)        # 4xx 不重试


class TestDaemonControl(unittest.TestCase):
    def test_pid_liveness(self):
        import os
        from mnemo.cli import _daemon_pid
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        self.assertIsNone(_daemon_pid(cfg))                 # 无 pid 文件
        (cfg.home / "daemon.pid").write_text(str(os.getpid()))
        self.assertEqual(_daemon_pid(cfg), os.getpid())     # 当前进程存活
        (cfg.home / "daemon.pid").write_text("999999")
        self.assertIsNone(_daemon_pid(cfg))                 # 陈旧/不存在的 pid
        tmp.cleanup()


class TestPlaybook(unittest.TestCase):
    def test_run_executes_all_steps(self):
        import types as _types
        from mnemo.cli import cmd_playbook
        home = tempfile.mkdtemp()
        cfg = load_config(home)
        cfg.set("playbooks", {"晨间": ["echo: 第一步", "echo: 第二步"]})
        cfg.save()
        cmd_playbook(_types.SimpleNamespace(home=home, action="run", name="晨间",
                                            provider="offline", model=None, verbose=False))
        m = Memory(Path(home) / "mnemo.db")
        eps = m.session_episodes("playbook:晨间")
        self.assertEqual(len(eps), 2)               # 两步都执行
        m.close()


class TestWatch(unittest.TestCase):
    def test_file_watch_triggers_after_baseline(self):
        import os
        from mnemo.daemon import Scheduler, TaskStore
        tmp = tempfile.TemporaryDirectory()
        cfg = load_config(tmp.name)
        mem = Memory(cfg.db_path)
        agent = Agent(FakeProvider(["已处理变化", "再次处理"]),
                      build_default_registry(), mem, SkillRegistry(cfg), cfg)
        watched = Path(tmp.name) / "data.txt"
        watched.write_text("v1", encoding="utf-8")
        cfg.set("watch", [{"name": "w1", "path": str(watched), "prompt": "echo: changed"}])
        sched = Scheduler(agent, TaskStore(cfg.db_path), log=lambda *a: None)

        # 首次：只记录基线，不触发
        self.assertEqual(sched._check_watches(time.time()), 0)
        self.assertEqual(len(mem.session_episodes("watch")), 0)
        # 修改文件并把 mtime 推到未来 → 触发
        watched.write_text("v2", encoding="utf-8")
        future = time.time() + 1000
        os.utime(watched, (future, future))
        self.assertEqual(sched._check_watches(time.time()), 1)
        self.assertEqual(len(mem.session_episodes("watch")), 1)
        mem.close()
        tmp.cleanup()


class TestTaskHistory(unittest.TestCase):
    def test_runs_recorded_and_queried(self):
        from mnemo.daemon import TaskStore
        tmp = tempfile.TemporaryDirectory()
        store = TaskStore(Path(tmp.name) / "m.db")
        tid = store.add("t1", "do x", "@hourly")
        t = store.get(tid)
        store.mark_run(t, True, "done ok")
        store.mark_run(t, False, "ERROR: boom")
        runs = store.runs()
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["ok"], 0)      # 最新在前（失败那条）
        self.assertEqual(runs[0]["name"], "t1")
        self.assertEqual(len(store.runs(task_id=tid)), 2)
        tmp.cleanup()


class TestProfileCLI(unittest.TestCase):
    def test_set_get(self):
        import types as _types
        from mnemo.cli import cmd_profile
        home = tempfile.mkdtemp()
        cmd_profile(_types.SimpleNamespace(home=home, action="set", key="name",
                                           value="大硕", provider=None, model=None))
        m = Memory(Path(home) / "mnemo.db")
        self.assertEqual(m.get_profile("name"), "大硕")
        m.close()


class TestDiary(unittest.TestCase):
    def test_episodes_since(self):
        tmp = tempfile.TemporaryDirectory()
        mem = Memory(Path(tmp.name) / "m.db")
        mem.add_episode("s", "今天聊了登山", "好的")
        recent = mem.episodes_since(time.time() - 3600)
        self.assertEqual(len(recent), 1)
        self.assertEqual(mem.episodes_since(time.time() + 3600), [])  # 未来 → 空
        mem.close()
        tmp.cleanup()

    def test_diary_cli_stores_fact(self):
        import types as _types
        from mnemo.cli import cmd_diary
        home = tempfile.mkdtemp()
        # 先制造一条今日对话
        m0 = Memory(Path(home) / "mnemo.db")
        m0.add_episode("default", "我今天去爬山了", "真棒")
        m0.close()
        cmd_diary(_types.SimpleNamespace(home=home, days=1, provider="offline",
                                         model=None, verbose=False))
        m = Memory(Path(home) / "mnemo.db")
        self.assertTrue(any(f["kind"] == "diary" for f in m.all_facts()))
        m.close()


class TestMemoryImportCLI(unittest.TestCase):
    def test_import_json_and_text(self):
        import types as _types
        from mnemo.cli import cmd_memory
        home = tempfile.mkdtemp()
        jf = Path(home) / "f.json"
        jf.write_text(_json.dumps(["事实A", {"text": "事实B", "importance": 4}]),
                      encoding="utf-8")
        cmd_memory(_types.SimpleNamespace(home=home, action="import", file=str(jf),
                                          provider=None, model=None))
        m = Memory(Path(home) / "mnemo.db")
        got = [f["text"] for f in m.facts_by(source="import")]
        self.assertIn("事实A", got)
        self.assertIn("事实B", got)
        m.close()


class TestReviewFixes2(unittest.TestCase):
    """第二轮自动评审（2026-06-17）的修复回归。"""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_skill_name_traversal_rejected(self):
        with self.assertRaises(ValueError):
            self.skills.learn(name="../evil", text="x")
        with self.assertRaises(ValueError):
            self.skills.scaffold("/abs/pwn")

    def test_pricing_longest_prefix_wins(self):
        from mnemo.usage import price_for
        self.cfg.set("pricing", {"gpt-4": {"in": 1000, "out": 1000},
                                 "gpt-4o-mini": {"in": 1, "out": 1}})
        cost = price_for(self.cfg, "gpt-4o-mini-2024-07-18", 1_000_000, 0)
        self.assertAlmostEqual(cost, 1.0)            # 命中更长的 gpt-4o-mini

    def test_daily_schedule_validation(self):
        from mnemo.daemon import parse_schedule
        self.assertEqual(parse_schedule("@daily"), ("daily", (9, 0)))
        self.assertEqual(parse_schedule("@daily 09:30"), ("daily", (9, 30)))
        with self.assertRaises(ValueError):
            parse_schedule("@daily 25:00")
        with self.assertRaises(ValueError):
            parse_schedule("@daily nonsense")

    def test_json_in_prose_not_executed(self):
        # 围栏内、整条 JSON → 识别为工具调用
        self.assertEqual(parse_tool_call('```tool\n{"name":"now","args":{}}\n```'), ("now", {}))
        self.assertEqual(parse_tool_call('{"name":"now","args":{}}'), ("now", {}))
        # 正文里举例的 JSON（前后有散文）→ 不执行
        self.assertIsNone(
            parse_tool_call('示例：{"name":"write_file","args":{"path":"a"}} 仅供参考'))

    def test_native_summary_after_exhaustion(self):
        class AlwaysToolProvider(Provider):
            name = "alwaystool"

            def chat(self, messages, **kw):
                return "x"

            def supports_tools(self):
                return True

            def chat_tools(self, messages, specs, **kw):
                if messages and messages[-1].role == "user" \
                        and "最终回答" in messages[-1].content:
                    return {"text": "基于观察的总结", "tool_calls": []}
                return {"text": "", "tool_calls": [{"id": "1", "name": "now", "args": {}}]}

        self.cfg.set("native_tools", True)
        self.cfg.set("max_steps", 2)
        agent = Agent(AlwaysToolProvider(), self.tools, self.mem, self.skills, self.cfg)
        out = agent.run("几点了")
        self.assertEqual(out, "基于观察的总结")


_DDG_SAMPLE = '''<html><body>
<div class="result results_links web-result">
 <h2 class="result__title">
  <a rel="nofollow" class="result__a"
     href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FMars&amp;rut=abc">Mars - <b>Wikipedia</b></a>
 </h2>
 <a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">Mars is the fourth planet from the Sun.</a>
</div>
<div class="result">
 <h2 class="result__title">
  <a rel="nofollow" class="result__a"
     href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnasa.gov%2Fmars&amp;rut=def">NASA Mars</a>
 </h2>
 <a class="result__snippet">Explore Mars with NASA.</a>
</div>
</body></html>'''


class TestWebSearch(unittest.TestCase):
    def test_parse_results(self):
        from mnemo.websearch import parse_results
        res = parse_results(_DDG_SAMPLE)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["title"], "Mars - Wikipedia")     # <b> 被剥离
        self.assertEqual(res[0]["url"], "https://en.wikipedia.org/wiki/Mars")  # uddg 解码 + &amp;
        self.assertEqual(res[0]["snippet"], "Mars is the fourth planet from the Sun.")
        self.assertEqual(res[1]["url"], "https://nasa.gov/mars")

    def test_parse_limit(self):
        from mnemo.websearch import parse_results
        self.assertEqual(len(parse_results(_DDG_SAMPLE, limit=1)), 1)

    def test_tool_formats_results(self):
        import mnemo.websearch as ws
        from mnemo.websearch import parse_results
        orig = ws.search
        ws.search = lambda q, limit=6: parse_results(_DDG_SAMPLE, limit)
        try:
            reg = build_default_registry()
            out = reg.run("web_search", {"query": "mars"}, ToolContext())
        finally:
            ws.search = orig
        self.assertIn("Mars - Wikipedia", out)
        self.assertIn("https://en.wikipedia.org/wiki/Mars", out)

    def test_tool_handles_network_error(self):
        import mnemo.websearch as ws
        def boom(q, limit=6):
            raise OSError("network down")
        orig = ws.search
        ws.search = boom
        try:
            out = build_default_registry().run("web_search", {"query": "x"}, ToolContext())
        finally:
            ws.search = orig
        self.assertIn("检索失败", out)


class TestUsage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(self.tmp.name)
        self.mem = Memory(self.cfg.db_path)
        self.skills = SkillRegistry(self.cfg)
        self.tools = build_default_registry()

    def tearDown(self):
        self.mem.close()
        self.tmp.cleanup()

    def test_estimate_tokens(self):
        from mnemo.usage import estimate_tokens
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("你好世界"), 4)        # 4 个 CJK 字
        self.assertGreaterEqual(estimate_tokens("hello world"), 2)

    def test_price_for_exact_and_prefix(self):
        from mnemo.usage import price_for
        self.cfg.set("pricing", {"m1": {"in": 1000, "out": 2000}})
        self.assertAlmostEqual(price_for(self.cfg, "m1", 100, 20), 0.1 + 0.04)
        # 前缀匹配
        self.assertAlmostEqual(price_for(self.cfg, "m1-2026", 100, 0), 0.1)
        # 未配置 → 0
        self.assertEqual(price_for(self.cfg, "unknown", 100, 20), 0.0)

    def test_store_record_and_summary(self):
        from mnemo.usage import UsageStore
        store = UsageStore(self.cfg.db_path)
        store.record(session="s", provider="p", model="m1", in_tok=10, out_tok=5,
                     estimated=True, cost=0.0)
        store.record(session="s", provider="p", model="m1", in_tok=20, out_tok=8,
                     estimated=False, cost=0.5)
        s = store.summary()
        self.assertEqual(s["calls"], 2)
        self.assertEqual(s["in_tok"], 30)
        self.assertEqual(s["out_tok"], 13)
        self.assertEqual(s["estimated"], 1)
        self.assertAlmostEqual(s["cost"], 0.5)
        self.assertEqual(store.by_model()[0]["model"], "m1")
        store.close()

    def test_agent_records_estimated_usage(self):
        from mnemo.usage import UsageStore
        store = UsageStore(self.cfg.db_path)
        agent = Agent(FakeProvider(["最终答案"]), self.tools, self.mem, self.skills,
                      self.cfg, usage=store)
        agent.run("问题一二三")
        s = store.summary()
        self.assertEqual(s["calls"], 1)
        self.assertEqual(s["estimated"], 1)        # FakeProvider 无真实用量 → 估算
        self.assertGreater(s["in_tok"], 0)
        store.close()

    def test_agent_uses_real_usage_when_available(self):
        from mnemo.usage import UsageStore

        class UsageProvider(Provider):
            name = "usagefake"

            def chat(self, messages, **kw):
                self.last_usage = {"in": 100, "out": 20}
                return "答案"

        store = UsageStore(self.cfg.db_path)
        self.cfg.set("pricing", {"m1": {"in": 1000, "out": 2000}})
        agent = Agent(UsageProvider(model="m1"), self.tools, self.mem, self.skills,
                      self.cfg, usage=store)
        agent.run("hi")
        s = store.summary()
        self.assertEqual(s["estimated"], 0)        # 用了真实用量
        self.assertEqual(s["in_tok"], 100)
        self.assertEqual(s["out_tok"], 20)
        self.assertAlmostEqual(s["cost"], 0.14)
        store.close()

    def test_daily_budget_blocks_calls(self):
        from mnemo.usage import UsageStore
        store = UsageStore(self.cfg.db_path)
        store.record(session="s", provider="p", model="m", in_tok=60, out_tok=60,
                     estimated=True)
        self.cfg.set("usage.daily_token_limit", 10)

        class BoomProvider(Provider):
            name = "boom"
            def chat(self, messages, **kw):
                raise AssertionError("over budget: must not call provider")

        agent = Agent(BoomProvider(), self.tools, self.mem, self.skills, self.cfg, usage=store)
        out = agent.run("hi")
        self.assertIn("预算", out)               # 友好提示，未触发 BoomProvider
        store.close()

    def test_capture_usage_field_mapping(self):
        op = OpenAIProvider()
        op._capture_usage({"usage": {"prompt_tokens": 7, "completion_tokens": 3}})
        self.assertEqual(op.last_usage, {"in": 7, "out": 3})
        ap = AnthropicProvider()
        ap._capture_usage({"usage": {"input_tokens": 11, "output_tokens": 4}})
        self.assertEqual(ap.last_usage, {"in": 11, "out": 4})


# 一个最小可用的 MCP 服务（stdio JSON-RPC），用于端到端验证客户端，无需任何外部依赖。
_FAKE_MCP_SERVER = r'''
import sys, json
def send(o): sys.stdout.write(json.dumps(o)+"\n"); sys.stdout.flush()
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    m=json.loads(line); i=m.get("id"); method=m.get("method")
    if method=="initialize":
        send({"jsonrpc":"2.0","id":i,"result":{"protocolVersion":"2024-11-05",
            "capabilities":{"tools":{},"resources":{}},"serverInfo":{"name":"fake","version":"9.9"}}})
    elif method=="notifications/initialized":
        pass
    elif method=="tools/list":
        send({"jsonrpc":"2.0","id":i,"result":{"tools":[{"name":"echo",
            "description":"Echo back text","inputSchema":{"type":"object",
            "properties":{"text":{"type":"string","description":"text to echo"}},
            "required":["text"]}}]}})
    elif method=="resources/list":
        send({"jsonrpc":"2.0","id":i,"result":{"resources":[
            {"uri":"mem://note","name":"note"}]}})
    elif method=="resources/read":
        send({"jsonrpc":"2.0","id":i,"result":{"contents":[
            {"uri":m.get("params",{}).get("uri"),"text":"资源内容X"}]}})
    elif method=="tools/call":
        p=m.get("params",{}); a=p.get("arguments",{})
        if p.get("name")=="echo":
            send({"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text",
                "text":"echo: "+str(a.get("text",""))}]}})
        else:
            send({"jsonrpc":"2.0","id":i,"error":{"code":-32601,"message":"unknown tool"}})
    elif i is not None:
        send({"jsonrpc":"2.0","id":i,"error":{"code":-32601,"message":"unknown method"}})
'''


class TestMCP(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = Path(self.tmp.name) / "fake_mcp.py"
        self.server.write_text(_FAKE_MCP_SERVER, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _client(self):
        from mnemo.mcp import MCPClient
        return MCPClient("fake", sys.executable, [str(self.server)], timeout=15).start()

    def test_client_handshake_list_and_call(self):
        c = self._client()
        try:
            self.assertEqual(c.server_info.get("name"), "fake")
            tools = c.list_tools()
            self.assertEqual([t["name"] for t in tools], ["echo"])
            out = c.call_tool("echo", {"text": "hi"})
            self.assertEqual(out, "echo: hi")
        finally:
            c.close()

    def test_params_from_schema_marks_required(self):
        from mnemo.mcp import _params_from_schema
        params = _params_from_schema({"type": "object",
            "properties": {"text": {"type": "string", "description": "t"}},
            "required": ["text"]})
        self.assertIn("（必填）", params["text"])

    def test_manager_registers_into_registry(self):
        from mnemo.mcp import MCPManager
        cfg = load_config(self.tmp.name)
        cfg.set("mcp.servers", {"fake": {"command": sys.executable,
                                          "args": [str(self.server)]}})
        reg = build_default_registry()
        mgr = MCPManager(cfg)
        try:
            counts = mgr.connect_all(reg)
            self.assertEqual(counts.get("fake"), 1)
            self.assertIn("mcp__fake__echo", reg.names())   # provider 安全名（无点号）
            self.assertNotIn("fake.echo", reg.names())
            ctx = ToolContext(cwd=self.tmp.name, config=cfg)
            self.assertEqual(reg.run("mcp__fake__echo", {"text": "yo"}, ctx), "echo: yo")
            # 外部 MCP 工具应被标记为高危（受 confirm_danger 约束）
            self.assertTrue(reg.get("mcp__fake__echo").danger)
        finally:
            mgr.close_all()

    def test_missing_command_raises(self):
        from mnemo.mcp import MCPClient, MCPError
        with self.assertRaises(MCPError):
            MCPClient("nope", "definitely-not-a-real-binary-xyz", []).start()

    def test_tool_alias_is_provider_safe(self):
        import re as _re
        from mnemo.mcp import tool_alias
        a = tool_alias("my.server", "read-file")
        self.assertEqual(a, "mcp__my_server__read-file")
        self.assertTrue(_re.fullmatch(r"[A-Za-z0-9_-]+", a))   # 无点号，原生可用

    def test_resources_registered_and_readable(self):
        from mnemo.mcp import MCPManager
        cfg = load_config(self.tmp.name)
        cfg.set("mcp.servers", {"fake": {"command": sys.executable,
                                          "args": [str(self.server)]}})
        reg = build_default_registry()
        mgr = MCPManager(cfg)
        try:
            mgr.connect_all(reg)
            alias = "mcp__fake__read_resource"
            self.assertIn(alias, reg.names())
            ctx = ToolContext(cwd=self.tmp.name, config=cfg)
            listing = reg.run(alias, {}, ctx)            # 不传 uri → 列资源
            self.assertIn("mem://note", listing)
            content = reg.run(alias, {"uri": "mem://note"}, ctx)
            self.assertEqual(content, "资源内容X")
        finally:
            mgr.close_all()


if __name__ == "__main__":
    unittest.main(verbosity=2)
