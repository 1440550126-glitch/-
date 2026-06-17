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
            "capabilities":{"tools":{}},"serverInfo":{"name":"fake","version":"9.9"}}})
    elif method=="notifications/initialized":
        pass
    elif method=="tools/list":
        send({"jsonrpc":"2.0","id":i,"result":{"tools":[{"name":"echo",
            "description":"Echo back text","inputSchema":{"type":"object",
            "properties":{"text":{"type":"string","description":"text to echo"}},
            "required":["text"]}}]}})
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
            self.assertIn("fake.echo", reg.names())
            ctx = ToolContext(cwd=self.tmp.name, config=cfg)
            self.assertEqual(reg.run("fake.echo", {"text": "yo"}, ctx), "echo: yo")
            # 外部 MCP 工具应被标记为高危（受 confirm_danger 约束）
            self.assertTrue(reg.get("fake.echo").danger)
        finally:
            mgr.close_all()

    def test_missing_command_raises(self):
        from mnemo.mcp import MCPClient, MCPError
        with self.assertRaises(MCPError):
            MCPClient("nope", "definitely-not-a-real-binary-xyz", []).start()


if __name__ == "__main__":
    unittest.main(verbosity=2)
