"""Mnemo 命令行入口：把 provider / 记忆 / 工具 / 技能 / 插件 / 守护进程串起来。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .agent import Agent
from .config import load_config
from .memory import Memory
from .plugins import PluginManager
from .providers import Message, ProviderError, build_provider, provider_status
from .skills import SkillRegistry
from .tools import build_default_registry

_TTY = sys.stdout.isatty()


def _c(s, code):
    return f"\033[{code}m{s}\033[0m" if _TTY else str(s)


def dim(s): return _c(s, "2")
def cyan(s): return _c(s, "36")
def bold(s): return _c(s, "1")
def green(s): return _c(s, "32")
def red(s): return _c(s, "31")
def yellow(s): return _c(s, "33")


@dataclass
class App:
    cfg: object
    provider: object
    memory: object
    tools: object
    skills: object
    plugins: object
    agent: object
    mcp: object = None
    usage: object = None


def build_app(args, check_same_thread: bool = True, with_mcp: bool = False) -> App:
    cfg = load_config(getattr(args, "home", None))
    if getattr(args, "provider", None):
        cfg.set("provider", args.provider)
    if getattr(args, "model", None):
        cfg.set("model", args.model)
    memory = (Memory(cfg.db_path, check_same_thread=check_same_thread)
              if cfg.get("memory.enabled", True) else None)
    tools = build_default_registry()
    skills = SkillRegistry(cfg)
    plugins = PluginManager(cfg, tools, skills)
    plugins.load_all()
    mcp = None
    if with_mcp and cfg.get("mcp.servers", {}):
        from .mcp import MCPManager
        mcp = MCPManager(cfg)
        counts = mcp.connect_all(tools)
        for name, n in counts.items():
            print(dim(f"  ⚙ MCP {name}: 接入 {n} 个工具"))
        for name, err in mcp.errors.items():
            print(yellow(f"  ⚠ MCP {name} 连接失败：{err}"))
    usage = None
    if cfg.get("usage.enabled", True):
        from .usage import UsageStore
        usage = UsageStore(cfg.db_path, check_same_thread=check_same_thread)
    provider = build_provider(cfg)
    agent = Agent(provider, tools, memory, skills, cfg, usage=usage)
    return App(cfg, provider, memory, tools, skills, plugins, agent, mcp, usage)


def _make_on_event(verbose: bool):
    def on_event(kind, data):
        if kind == "tool":
            print(dim(f"  ⚙ {data['name']}({json.dumps(data['args'], ensure_ascii=False)})"))
        elif kind == "observation":
            r = str(data["result"]).replace("\n", " ")
            print(dim(f"  ↳ {r[:160]}{'…' if len(r) > 160 else ''}"))
        elif kind == "learned":
            print(dim(f"  ✦ 记住：{'；'.join(data['items'])}"))
        elif kind == "think" and verbose:
            print(dim(f"  · 思考第 {data['step']} 步"))
    return on_event


# ---------------- 子命令 ----------------

def cmd_chat(args):
    app = build_app(args, with_mcp=True)
    p = app.provider
    print(bold("✦ Mnemo") + dim(f"  {p.name}/{p.model or 'default'}  ·  /help 命令  ·  /exit 退出"))
    if app.memory:
        prof = app.memory.profile_summary()
        if prof:
            print(dim("我对你的了解：\n" + prof))
    on_event = _make_on_event(args.verbose)
    session = getattr(args, "session", None) or "default"
    if getattr(args, "resume", False) and app.memory:
        sess = app.memory.sessions()
        if sess:
            session = sess[0]["session"]
            print(dim(f"↩ 续接会话：{session}（{sess[0]['c']} 轮）"))
    confirm_danger = app.cfg.get("tools.confirm_danger", False) and _TTY

    def _confirm(msg):
        try:
            return input(yellow(f"{msg} [y/N] ")).strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
    while True:
        try:
            line = input(cyan("\n你 › ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见 👋")
            break
        if not line:
            continue
        if line in ("/exit", "/quit"):
            print("再见 👋")
            break
        if line == "/help":
            print(dim("/memory 记忆  /profile 画像  /skills 技能  /tools 工具  /provider 后端\n"
                      "/usage 用量  /reminders 提醒  /persona [名] 人格  /ingest <路径> 摄入知识\n"
                      "/forget <id> 删记忆  /distill <名> 存技能  /new 新会话  /exit 退出"))
            continue
        if line.startswith("/distill "):
            from .skills import distill_from_trace
            nm = line.split(maxsplit=1)[1].strip()
            if not app.agent.last_trace:
                print(dim("还没有可提炼的对话"))
                continue
            text = distill_from_trace(app.agent.last_trace, app.provider, nm)
            s = app.skills.learn(name=nm, text=text)
            print(dim(f"✦ 已学会技能：{s.name} → {s.path}"))
            continue
        if line == "/memory" and app.memory:
            s = app.memory.stats()
            print(dim(f"事实 {s['facts']} · 对话 {s['episodes']} · 话题 {s['topics']}"))
            for f in app.memory.all_facts(limit=10):
                print(dim(f"  #{f['id']} [{f['kind']}] {f['text']}"))
            continue
        if line == "/profile" and app.memory:
            print(dim(app.memory.profile_summary() or "(还没积累到画像)"))
            continue
        if line == "/skills":
            for s in app.skills.list():
                print(dim(f"  {s.name} — {s.description}"))
            continue
        if line == "/provider":
            for st in provider_status(app.cfg):
                mark = green("●") if st["available"] else dim("○")
                print(f"  {mark} {st['name']} ({st.get('model')})")
            continue
        if line.startswith("/forget ") and app.memory:
            ok = app.memory.forget(int(line.split()[1]))
            print(dim("已删除" if ok else "未找到"))
            continue
        if line == "/new":
            session = f"chat:{int(time.time())}"
            print(dim("已开启新会话"))
            continue
        if line == "/tools":
            print(dim("可用工具：" + "、".join(app.tools.names())))
            continue
        if line == "/usage":
            from .usage import UsageStore
            us = UsageStore(app.cfg.db_path)
            s = us.summary(); us.close()
            print(dim(f"累计 {s['calls']} 次 · 入 {s['in_tok']} · 出 {s['out_tok']}"
                      + (f" · ${s['cost']:.4f}" if s['cost'] else "")))
            continue
        if line == "/reminders" and app.memory:
            rows = app.memory.pending_reminders()
            print(dim("（无待办提醒）") if not rows else
                  "\n".join(dim(f"  {time.strftime('%m-%d %H:%M', time.localtime(r['remind_at']))} "
                                f"{r['text']}") for r in rows))
            continue
        if line.startswith("/persona"):
            parts = line.split(maxsplit=1)
            if len(parts) == 1:
                cur = app.cfg.get("persona_active") or "（默认）"
                names = ", ".join((app.cfg.get("personas", {}) or {}).keys())
                print(dim(f"当前人格：{cur}　可选：{names or '无'}（/persona <名> 切换）"))
            else:
                name = parts[1].strip()
                if name in (app.cfg.get("personas", {}) or {}):
                    app.cfg.set("persona_active", name); app.cfg.save()
                    print(dim(f"✦ 已切换人格 → {name}"))
                else:
                    print(dim(f"未找到人格：{name}"))
            continue
        if line.startswith("/ingest ") and app.memory:
            from .ingest import ingest_path
            p = Path(line.split(maxsplit=1)[1].strip()).expanduser()
            if not p.exists():
                print(dim(f"路径不存在：{p}")); continue
            res = ingest_path(app.memory, p, provider=app.provider)
            print(dim(f"✦ 已摄入 {res['files']} 文件 / {res['chunks']} 块"))
            continue
        streaming = (_TTY and app.cfg.get("ui.stream", True)
                     and not app.cfg.get("native_tools", False))
        state = {"started": False}

        def on_token(t):
            if not state["started"]:
                sys.stdout.write("\n" + bold("Mnemo › "))
                state["started"] = True
            sys.stdout.write(t)
            sys.stdout.flush()
        try:
            reply = app.agent.run(line, session=session, on_event=on_event,
                                   auto_approve=not confirm_danger, confirm=_confirm,
                                   on_token=on_token if streaming else None)
            if state["started"]:
                print()                      # 流式收尾换行
            else:
                print(bold("Mnemo › ") + reply)
        except ProviderError as e:
            if state["started"]:
                print()
            print(red(f"[模型调用失败] {e}"))


def cmd_run(args):
    app = build_app(args, with_mcp=True)
    as_json = getattr(args, "json", False)
    try:
        out = app.agent.run(args.prompt, cwd=args.cwd,
                            session=getattr(args, "session", None) or "default",
                            on_event=None if as_json else _make_on_event(args.verbose))
    except ProviderError as e:
        if as_json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(red(f"[模型调用失败] {e}"), file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps({"reply": out, "steps": app.agent.last_trace.get("steps", [])},
                         ensure_ascii=False, indent=2))
    else:
        print(out)
    if getattr(args, "distill", None):
        from .skills import distill_from_trace
        text = distill_from_trace(app.agent.last_trace, app.provider, args.distill)
        s = app.skills.learn(name=args.distill, text=text)
        print(dim(f"✦ 已把本次过程沉淀为技能：{s.name}"), file=sys.stderr)
    return 0


def cmd_ingest(args):
    app = build_app(args)
    if not app.memory:
        print(red("记忆未启用，无法摄入知识")); return 1
    import re as _re
    from .ingest import ingest_path, ingest_url
    prov = None if args.no_embed else app.provider
    try:
        if _re.match(r"^https?://", args.path):          # 摄入网页
            res = ingest_url(app.memory, args.path, tag=args.tag or "",
                             max_chars=args.max_chars, provider=prov)
        else:                                            # 摄入文件/目录
            p = Path(args.path).expanduser()
            if not p.exists():
                print(red(f"路径不存在：{p}")); return 1
            res = ingest_path(app.memory, p, tag=args.tag or "",
                              max_chars=args.max_chars, provider=prov)
    except Exception as e:  # noqa: BLE001
        print(red(f"摄入失败：{e}")); return 1
    if not res["chunks"]:
        print(yellow("没有可摄入的文本（检查扩展名/大小限制）")); return 0
    msg = f"已摄入 {res['files']} 个文件 · {res['chunks']} 个知识块"
    if res.get("embedded"):
        msg += f" · 向量化 {res['embedded']} 块"
    if res.get("skipped"):
        msg += dim(f" · 跳过 {res['skipped']}")
    print(green(msg))
    print(dim("用 `mnemo memory search <词>` 检索；相关对话时会被自动回忆。"))
    return 0


def cmd_config(args):
    app_cfg = load_config(getattr(args, "home", None))
    if args.action == "path":
        print(app_cfg.config_file)
    elif args.action == "show":
        print(json.dumps(app_cfg.data, ensure_ascii=False, indent=2))
    elif args.action == "get":
        print(app_cfg.get(args.key))
    elif args.action == "set":
        try:
            val = json.loads(args.value)
        except json.JSONDecodeError:
            val = args.value
        app_cfg.set(args.key, val)
        app_cfg.save()
        print(green(f"已设置 {args.key} = {val!r}"))
    return 0


def cmd_persona(args):
    cfg = load_config(getattr(args, "home", None))
    personas = dict(cfg.get("personas", {}) or {})
    active = cfg.get("persona_active")
    if args.action == "list":
        if not personas:
            print(dim("（暂无命名人格）用 mnemo persona add <名> <提示> 添加"))
        for name, text in personas.items():
            mark = green("●") if name == active else dim("○")
            print(f"{mark} {bold(name)} — {dim(text[:60])}")
        print(dim(f"\n当前：{active or '（默认 persona）'}"))
    elif args.action == "show":
        text = personas.get(args.name) or (cfg.get("persona") if args.name == "默认" else None)
        print(text or red("未找到"))
    elif args.action == "add":
        personas[args.name] = args.prompt
        cfg.set("personas", personas); cfg.save()
        print(green(f"已保存人格：{args.name}"))
    elif args.action == "use":
        if args.name not in personas:
            print(red(f"未找到人格：{args.name}（可用：{', '.join(personas) or '无'}）")); return 1
        cfg.set("persona_active", args.name); cfg.save()
        print(green(f"已切换人格 → {args.name}"))
    elif args.action == "reset":
        cfg.set("persona_active", None); cfg.save()
        print(green("已恢复默认 persona"))
    elif args.action == "remove":
        if personas.pop(args.name, None) is None:
            print(red("未找到")); return 1
        if active == args.name:
            cfg.set("persona_active", None)
        cfg.set("personas", personas); cfg.save()
        print(green(f"已删除人格：{args.name}"))
    return 0


def cmd_provider(args):
    cfg = load_config(getattr(args, "home", None))
    if getattr(args, "provider", None):
        cfg.set("provider", args.provider)
    if getattr(args, "model", None):
        cfg.set("model", args.model)
    # 加载插件，使其注册的自定义 provider 也能被 list/test 看到（与 build_app 行为一致）
    PluginManager(cfg, build_default_registry(), SkillRegistry(cfg)).load_all()
    if args.action == "list":
        for st in provider_status(cfg):
            mark = green("● 就绪") if st["available"] else dim("○ 未就绪")
            extra = f"  {st['error']}" if st.get("error") else ""
            print(f"{mark}  {bold(st['name']):<12} 模型={st.get('model')}{dim(extra)}")
        cur = (cfg.get("provider") or "auto")
        print(dim(f"\n当前 provider 配置：{cur}（auto 会自动挑可用后端）"))
    elif args.action == "test":
        p = build_provider(cfg)
        print(dim(f"测试 {p.name}/{p.model} …"))
        try:
            out = p.chat([Message("user", "用一句话介绍你自己")], max_tokens=128)
            print(green("OK：") + out)
        except ProviderError as e:
            print(red(f"FAIL：{e}"))
            return 1
    return 0


def cmd_memory(args):
    app = build_app(args)
    m = app.memory
    if not m:
        print("记忆已禁用（memory.enabled=false）")
        return 0
    if args.action == "list":
        if getattr(args, "kind", None) or getattr(args, "tag", None) or getattr(args, "source", None):
            facts = m.facts_by(kind=args.kind, tag=args.tag, source=args.source, limit=args.limit)
        else:
            facts = m.all_facts(limit=args.limit)
        if not facts:
            print(dim("（无匹配记忆）"))
        for f in facts:
            src = dim(f"  «{f['source']}»") if f.get("source") not in (None, "user") else ""
            print(f"#{f['id']:<4} [{f['kind']}] 重要度{f['importance']}  {f['text'][:80]}{src}")
    elif args.action == "forget-source":
        n = m.forget_by_source(args.source)
        print(green(f"已删除 {n} 条来源以「{args.source}」开头的记忆") if n else yellow("未匹配到记忆"))
    elif args.action == "export":
        out = Path(args.out)
        out.write_text(m.export_markdown(), encoding="utf-8")
        print(green(f"已导出记忆 → {out}"))
    elif args.action == "import":
        p = Path(args.file)
        if not p.is_file():
            print(red(f"文件不存在：{p}")); return 1
        n = 0
        if p.suffix == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(red(f"JSON 解析失败：{e}")); return 1
            for it in (data if isinstance(data, list) else []):
                if isinstance(it, str) and it.strip():
                    m.add_fact(it.strip(), source="import"); n += 1
                elif isinstance(it, dict) and it.get("text"):
                    m.add_fact(it["text"], kind=it.get("kind", "fact"),
                               importance=int(it.get("importance", 3)),
                               tags=it.get("tags", ""), source=it.get("source", "import"))
                    n += 1
        else:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    m.add_fact(line, source="import"); n += 1
        print(green(f"已导入 {n} 条记忆"))
    elif args.action == "search":
        for f in m.recall(args.query, limit=args.limit):
            print(f"#{f['id']:<4} {f['text']}")
    elif args.action == "add":
        fid = m.add_fact(args.text, kind=args.kind, importance=args.importance)
        print(green(f"已记住 #{fid}"))
    elif args.action == "forget":
        print(green("已删除") if m.forget(args.id) else red("未找到"))
    elif args.action == "profile":
        print(m.profile_summary() or "(还没积累到画像)")
    elif args.action == "stats":
        print(json.dumps(m.stats(), ensure_ascii=False, indent=2))
    elif args.action == "consolidate":
        res = m.consolidate()
        print(green(f"记忆巩固完成：合并 {res['merged']}，淡忘 {res['forgotten']}，"
                    f"保留 {res['kept']}"))
    elif args.action == "backfill":
        n = m.embed_backfill(app.provider)
        print(green(f"已为 {n} 条记忆补算语义向量") if n
              else yellow("无可补算（当前后端无 embed 能力，或已全部完成）"))
    elif args.action == "remind":
        from .memory import parse_when
        when = parse_when(args.when)
        if when is None:
            print(red("无法解析时间，请用：in 2h / 18:30 / 2026-06-17 09:00"))
            return 1
        rid = m.add_reminder(args.text, when)
        print(green(f"已设提醒 #{rid}（{time.strftime('%m-%d %H:%M', time.localtime(when))}）"
                    + dim("，启动 mnemo daemon 后到点会主动触发")))
    elif args.action == "reminders":
        rows = m.pending_reminders()
        if not rows:
            print(dim("（无待办提醒）"))
        for r in rows:
            when = time.strftime("%m-%d %H:%M", time.localtime(r["remind_at"]))
            print(f"#{r['id']:<3} {when}  {r['text']}")
    elif args.action == "graph":
        from .viz import render_graph_html
        data = m.graph(limit=args.limit)
        out = Path(args.out)
        out.write_text(render_graph_html(data), encoding="utf-8")
        print(green(f"已生成记忆图谱：{out}") +
              dim(f"（{len(data['nodes'])} 节点 / {len(data['edges'])} 关联，浏览器打开查看）"))
    return 0


def cmd_session(args):
    app = build_app(args)
    m = app.memory
    if not m:
        print("记忆已禁用"); return 0
    if args.action == "summarize":
        summ = m.summarize_session(args.session, app.provider)
        if summ:
            print(green("已生成会话摘要：") + "\n" + dim(summ))
        else:
            print(yellow("无法生成摘要（对话太短，或当前后端不支持/离线）"))
        return 0
    if args.action == "list":
        rows = m.sessions()
        if not rows:
            print(dim("（暂无会话记录）")); return 0
        for r in rows:
            last = time.strftime("%m-%d %H:%M", time.localtime(r["last_at"])) if r["last_at"] else "—"
            print(f"{bold(r['session']):<22} {r['c']:>4} 轮   最近 {last}")
    elif args.action in ("show", "export"):
        eps = m.session_episodes(args.session)
        if not eps:
            print(yellow(f"会话「{args.session}」无记录")); return 1
        lines = [f"# 会话 {args.session}", ""]
        for e in eps:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(e["created_at"]))
            lines += [f"## {ts}", f"**你**：{e['user']}", "", f"**Mnemo**：{e['assistant']}", ""]
        text = "\n".join(lines)
        if args.action == "export":
            Path(args.out).write_text(text, encoding="utf-8")
            print(green(f"已导出会话 → {args.out}（{len(eps)} 轮）"))
        else:
            print(text)
    return 0


def cmd_skill(args):
    app = build_app(args)
    sk = app.skills
    if args.action == "list":
        for s in sk.list():
            tag = dim("[内置]" if s.builtin else "[自有]")
            print(f"{tag} {bold(s.name)} — {s.description}")
    elif args.action == "show":
        s = sk.get(args.name)
        if not s:
            print(red("未找到该技能"))
            return 1
        print(bold(s.name) + f"\n描述：{s.description}\n适用：{s.when_to_use}\n\n{s.body}")
    elif args.action == "run":
        s = sk.get(args.name)
        if not s:
            print(red(f"未找到技能：{args.name}")); return 1
        prompt = (f"运用技能「{s.name}」完成下面的任务：\n{args.input}\n\n"
                  f"[技能说明]\n{s.body}")
        try:
            out = app.agent.run(prompt, on_event=_make_on_event(args.verbose))
        except ProviderError as e:
            print(red(f"[模型调用失败] {e}")); return 1
        print(out)
    elif args.action == "new":
        print(green(f"已创建技能模板：{sk.scaffold(args.name)}"))
    elif args.action == "learn":
        s = sk.learn(name=args.name, from_file=args.file, from_url=args.url, text=args.text)
        print(green(f"已学会技能：{s.name} → {s.path}"))
    elif args.action == "remove":
        print(green("已删除") if sk.remove(args.name) else red("无法删除（不存在或为内置）"))
    elif args.action == "distill":
        from .skills import distill_from_trace
        trace_file = app.cfg.home / "last_trace.json"
        if not trace_file.is_file():
            print(red("没有可提炼的最近任务，先用 mnemo run 跑一个任务"))
            return 1
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        text = distill_from_trace(trace, app.provider, args.name)
        s = sk.learn(name=args.name, text=text)
        print(green(f"已把最近任务沉淀为技能：{s.name} → {s.path}"))
    return 0


def cmd_plugin(args):
    app = build_app(args)
    pm = app.plugins
    if args.action == "list":
        items = pm.list()
        if not items:
            print(dim("（尚无插件）插件目录：" + str(pm.dir)))
        for it in items:
            mark = green("●") if it.get("_loaded") else red("✗")
            err = red("  " + it["_error"]) if it.get("_error") else ""
            print(f"{mark} {bold(it.get('name'))} v{it.get('version','?')} — "
                  f"{it.get('description','')}{err}")
    elif args.action == "install":
        if _TTY and not args.yes:
            ans = input(yellow(f"插件会执行任意代码，确认从 {args.source} 安装？[y/N] "))
            if ans.strip().lower() not in ("y", "yes"):
                print("已取消")
                return 1
        try:
            name = pm.install(args.source, name=args.name)
            print(green(f"已安装并加载插件：{name}"))
        except Exception as e:  # noqa: BLE001
            print(red(f"安装失败：{e}"))
            return 1
    elif args.action == "remove":
        print(green("已移除") if pm.remove(args.name) else red("未找到"))
    return 0


def cmd_watch(args):
    cfg = load_config(getattr(args, "home", None))
    watches = list(cfg.get("watch", []) or [])
    if args.action == "list":
        if not watches:
            print(dim("（未配置监视）mnemo watch add --name X --path ./dir --prompt \"...\""))
        for w in watches:
            print(f"{green('●')} {bold(w.get('name'))} ← {dim(w.get('path'))}  «{w.get('prompt','')[:40]}»")
    elif args.action == "add":
        watches = [w for w in watches if w.get("name") != args.name]
        watches.append({"name": args.name, "path": args.path, "prompt": args.prompt})
        cfg.set("watch", watches); cfg.save()
        print(green(f"已添加监视：{args.name} ← {args.path}")
              + dim("（mnemo daemon 运行时生效，首次只记录基线）"))
    elif args.action == "remove":
        new = [w for w in watches if w.get("name") != args.name]
        if len(new) == len(watches):
            print(red("未找到")); return 1
        cfg.set("watch", new); cfg.save()
        print(green(f"已移除监视：{args.name}"))
    return 0


def cmd_mcp(args):
    cfg = load_config(getattr(args, "home", None))
    servers = dict(cfg.get("mcp.servers", {}) or {})
    if args.action == "list":
        if not servers:
            print(dim("（尚未配置 MCP 服务）添加：mnemo mcp add <名字> --command npx --arg -y "
                      "--arg @modelcontextprotocol/server-filesystem --arg /data"))
            return 0
        for name, spec in servers.items():
            cmd = " ".join([spec.get("command", "?"), *spec.get("args", [])])
            print(f"{green('●')} {bold(name)} — {dim(cmd)}")
        print(dim("\n用 `mnemo mcp test <名字>` 实际连接并查看其工具。"))
    elif args.action == "add":
        env = {}
        for kv in (args.env or []):
            k, _, v = kv.partition("=")
            if k:
                env[k] = v
        spec = {"command": args.command, "args": args.arg or []}
        if env:
            spec["env"] = env
        servers[args.name] = spec
        cfg.set("mcp.servers", servers)
        cfg.save()
        print(green(f"已添加 MCP 服务：{args.name}"))
    elif args.action == "remove":
        if servers.pop(args.name, None) is None:
            print(red("未找到")); return 1
        cfg.set("mcp.servers", servers)
        cfg.save()
        print(green(f"已移除 MCP 服务：{args.name}"))
    elif args.action == "test":
        from .mcp import MCPError, MCPManager, tool_alias
        mgr = MCPManager(cfg)
        try:
            info = mgr.probe(args.name)
        except MCPError as e:
            print(red(f"连接失败：{e}")); return 1
        si = info.get("server_info", {})
        print(green(f"已连接 {args.name}") + dim(f"  {si.get('name','?')} v{si.get('version','?')}"))
        tools = info.get("tools", [])
        print(dim(f"暴露 {len(tools)} 个工具：") if tools else dim("（无工具）"))
        for t in tools:
            print(f"  · {bold(tool_alias(args.name, t.get('name','')))} — "
                  f"{(t.get('description') or '').splitlines()[0][:80]}")
    return 0


def cmd_task(args):
    app = build_app(args)
    from .daemon import TaskStore
    store = TaskStore(app.cfg.db_path)
    if args.action == "add":
        try:
            tid = store.add(args.name, args.prompt, args.every)
        except ValueError as e:
            print(red(f"调度无效：{e}")); return 1
        print(green(f"已创建任务 #{tid}：{args.name}（{args.every}）"))
    elif args.action == "list":
        rows = store.list()
        if not rows:
            print(dim("（暂无任务）用 mnemo task add 添加"))
        for t in rows:
            nxt = time.strftime("%m-%d %H:%M", time.localtime(t.next_run)) if t.next_run else "—"
            state = green("on") if t.enabled else dim("off")
            print(f"#{t.id:<3} [{state}] {bold(t.name):<16} {t.schedule:<14} 下次:{nxt}  "
                  f"{dim((t.last_result or '')[:40])}")
    elif args.action == "history":
        rows = store.runs(task_id=getattr(args, "id", None), limit=args.limit)
        if not rows:
            print(dim("（暂无执行历史）")); return 0
        for r in rows:
            ts = time.strftime("%m-%d %H:%M", time.localtime(r["started_at"]))
            mark = green("✓") if r["ok"] else red("✗")
            out = (r["output"] or "").replace("\n", " ")[:60]
            print(f"{ts} {mark} #{r['task_id']} {bold(r.get('name') or '?'):<14} {dim(out)}")
    elif args.action == "rm":
        print(green("已删除") if store.remove(args.id) else red("未找到"))
    elif args.action in ("enable", "disable"):
        store.set_enabled(args.id, args.action == "enable")
        print(green(f"已{args.action}任务 #{args.id}"))
    elif args.action == "run":
        t = store.get(args.id)
        if not t:
            print(red("未找到"))
            return 1
        print(dim(f"运行任务 {t.name} …"))
        out = app.agent.run(t.prompt, session=f"daemon:{t.name}",
                            on_event=_make_on_event(args.verbose))
        store.mark_run(t, True, out)
        print(out)
    return 0


def _daemon_pid(cfg):
    import os
    pf = cfg.home / "daemon.pid"
    if not pf.is_file():
        return None
    try:
        pid = int(pf.read_text().strip())
    except (ValueError, OSError):
        return None
    try:
        os.kill(pid, 0)            # 探活，不发真正信号
        return pid
    except OSError:
        return None                # 进程已不在（陈旧 pid 文件）


def cmd_daemon(args):
    import os
    import signal as _sig
    if getattr(args, "status", False):
        cfg = load_config(getattr(args, "home", None))
        pid = _daemon_pid(cfg)
        print(green(f"守护进程运行中（PID {pid}）") if pid else dim("守护进程未运行"))
        return 0
    if getattr(args, "stop", False):
        cfg = load_config(getattr(args, "home", None))
        pid = _daemon_pid(cfg)
        if not pid:
            print(dim("守护进程未运行")); return 0
        os.kill(pid, _sig.SIGTERM)
        print(green(f"已发送停止信号给 PID {pid}"))
        return 0
    app = build_app(args, with_mcp=True)
    from .daemon import Scheduler, TaskStore
    if not args.once and _daemon_pid(app.cfg):
        print(yellow("已有守护进程在运行（mnemo daemon --status 查看）。")); return 1
    store = TaskStore(app.cfg.db_path)
    sched = Scheduler(app.agent, store)
    if args.once:
        n = sched.run_once()
        print(dim(f"本轮执行了 {n} 个到期任务"))
    else:
        sched.serve(interval=args.interval)
    return 0


def cmd_market(args):
    app = build_app(args)
    from . import market
    source = args.registry or app.cfg.get("registry")

    # 评分不需要 registry
    if args.action == "rate":
        market.rate(str(app.cfg.db_path), args.name, args.stars, args.note or "")
        print(green(f"已评分 {args.name}：{'★' * args.stars}"))
        return 0

    if not source:
        print(red("未配置市场。用 --registry <文件或URL>，或 mnemo config set registry <...>"))
        return 1
    try:
        reg = market.load_registry(source)
    except Exception as e:  # noqa: BLE001
        print(red(f"读取市场失败：{e}"))
        return 1
    key = args.key or app.cfg.get("registry_key")

    if args.action == "sign":
        signed = market.sign_registry(reg, key)
        out = Path(args.out or source)
        out.write_text(json.dumps(signed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(green(f"已签名并写入：{out}"))
        return 0
    if args.action == "verify":
        ok = market.verify_registry(reg, key) if key else False
        print(green("✓ 签名有效") if ok else red("✗ 签名无效或缺失/未提供 --key"))
        return 0 if ok else 1

    # list / search / install
    sig_state = ("✓已签名" if (key and market.verify_registry(reg, key))
                 else ("⚠未提供key" if reg.get("signature") else "⚠未签名"))
    ratings = market.ratings_summary(str(app.cfg.db_path))
    if args.action in ("list", "search"):
        print(dim(f"来源 {source} · {sig_state}"))
        res = market.search(reg, getattr(args, "query", "") or "")
        for kind, items in (("技能", res["skills"]), ("插件", res["plugins"])):
            print(bold(kind))
            for it in items:
                rt = ratings.get(it["name"])
                star = dim(f"  {rt['avg']}★×{rt['count']}") if rt else ""
                print(f"  {bold(it['name'])} — {it.get('description', '')}{star}")
    elif args.action == "install":
        # 提供了 key 就必须签名有效（缺签名也拒绝），坚守信任链
        if key and not market.verify_registry(reg, key):
            print(red("拒绝安装：提供了 --key 但 registry 签名缺失或校验失败"))
            return 1
        is_plugin = any(p.get("name") == args.name for p in reg.get("plugins", []))
        if is_plugin and _TTY and not args.yes:
            ans = input(yellow(f"市场插件 {args.name} 会执行任意代码，确认安装？[y/N] "))
            if ans.strip().lower() not in ("y", "yes"):
                print("已取消")
                return 1
        try:
            what = market.install(args.name, reg, app.skills, app.plugins)
            print(green(f"已从市场安装：{what}"))
        except Exception as e:  # noqa: BLE001
            print(red(f"安装失败：{e}"))
            return 1
    return 0


def cmd_sync(args):
    from . import sync
    cfg = load_config(getattr(args, "home", None))
    if args.action == "export":
        n = sync.export_bundle(cfg.home, Path(args.file), args.passphrase)
        tag = dim("（已加密）") if args.passphrase else dim("（明文，建议加 --passphrase）")
        print(green(f"已导出 {n} 字节 → {args.file}") + tag)
    elif args.action == "import":
        try:
            members = sync.import_bundle(Path(args.file), cfg.home, args.passphrase)
        except ValueError as e:
            print(red(str(e)))
            return 1
        print(green(f"已导入到 {cfg.home}：{', '.join(members)}"))
    return 0


def cmd_audit(args):
    cfg = load_config(getattr(args, "home", None))
    path = cfg.home / "audit.log"
    if not path.is_file():
        print(dim("（暂无审计记录）所有工具调用都会记录到 " + str(path)))
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()[-args.limit:]
    for ln in lines:
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ts = time.strftime("%m-%d %H:%M:%S", time.localtime(e["ts"]))
        mark = green("✓") if e.get("ok") else red("✗")
        depth = dim(f"d{e['depth']}") if e.get("depth") else "  "
        print(f"{ts} {mark} {depth} {bold(e['tool'])} "
              f"{dim(json.dumps(e.get('args', {}), ensure_ascii=False)[:80])}")
    return 0


def _fmt_tok(n: int) -> str:
    return f"{n/1e6:.2f}M" if n >= 1e6 else (f"{n/1e3:.1f}k" if n >= 1000 else str(n))


def cmd_usage(args):
    from .usage import UsageStore
    cfg = load_config(getattr(args, "home", None))
    store = UsageStore(cfg.db_path)
    now = time.time()
    spans = [("今日", now - 86400), ("近 7 天", now - 7 * 86400), ("累计", None)]
    print(bold("用量观测") + dim("  （token 计；成本仅在 config.pricing 配置后才计算）"))
    any_est = False
    for label, since in spans:
        s = store.summary(since)
        if not s["calls"]:
            print(f"  {label:<6} —")
            continue
        any_est = any_est or s["estimated"]
        cost = f"  ${s['cost']:.4f}" if s["cost"] else ""
        print(f"  {label:<6} {s['calls']} 次调用 · 入 {_fmt_tok(s['in_tok'])} · "
              f"出 {_fmt_tok(s['out_tok'])}{cost}")
    limit = int(cfg.get("usage.daily_token_limit", 0) or 0)
    if limit > 0:
        today = store.summary(now - 86400)
        used = today["in_tok"] + today["out_tok"]
        bar = green if used < limit else red
        print(bold("\n每日预算") + f"  {bar(str(used))} / {limit} tokens"
              + (red("　已超限，调用暂停") if used >= limit else ""))
    rows = store.by_model()
    if rows:
        print(bold("\n按模型（累计）"))
        for r in rows:
            cost = f"  ${r['cost']:.4f}" if r["cost"] else ""
            print(f"  {bold(r['model']):<22} {r['c']} 次 · 入 {_fmt_tok(r['i'])} · "
                  f"出 {_fmt_tok(r['o'])}{cost}")
    if any_est:
        print(dim("\n注：部分记录为本地估算（流式/本地/离线后端无精确用量），仅供趋势参考。"))
    store.close()
    return 0


def cmd_serve(args):
    app = build_app(args, check_same_thread=False, with_mcp=True)
    from .serve import serve
    serve(app, host=args.host, port=args.port, token=args.token)
    return 0


def cmd_speak(args):
    from .tools import ToolContext, build_default_registry
    print(build_default_registry().run("speak", {"text": args.text}, ToolContext()))
    return 0


def cmd_see(args):
    app = build_app(args)
    if not app.provider.supports_vision():
        print(yellow(f"当前后端 {app.provider.name} 不支持视觉，请配置 gpt-4o / claude 等"))
        return 1
    from .media import extract_frames, is_video
    try:
        if is_video(args.path):
            frames = extract_frames(args.path, n=3)
            if not frames:
                print(yellow("无法抽取视频帧（需要 ffmpeg）。"))
                return 1
            for i, fr in enumerate(frames, 1):
                print(bold(f"帧{i}: ") + app.provider.vision(fr, args.prompt))
        else:
            print(app.provider.vision(args.path, args.prompt))
    except ProviderError as e:
        print(red(f"[视觉调用失败] {e}"))
        return 1
    return 0


def cmd_voice(args):
    app = build_app(args)
    from . import voice
    miss = voice.missing()
    if any(k.startswith(("录音", "识别")) for k in miss):
        print(red("语音对话不可用，缺少：" + "、".join(miss)))
        print(dim("安装示例：apt install alsa-utils espeak ffmpeg；pip install openai-whisper"))
        return 1
    print(dim(f"每轮录音 {args.seconds}s，Ctrl-C 退出。"))
    try:
        while True:
            print(voice.converse_once(app, args.seconds))
            if args.once:
                break
    except KeyboardInterrupt:
        print("\n再见 👋")
    return 0


def cmd_notify(args):
    cfg = load_config(getattr(args, "home", None))
    from .notify import notify
    ch = notify(cfg, args.message, title=args.title)
    print(green(f"已通过 {ch} 渠道发送") if ch != "none" else yellow("通知已禁用（notify.channel=none）"))
    return 0


def cmd_init(args):
    cfg = load_config(getattr(args, "home", None))
    print(bold("✦ Mnemo 初始化向导"))
    if not _TTY:
        print(dim("非交互环境，已跳过向导。手动配置：\n"
                  "  export ANTHROPIC_API_KEY=... / OPENAI_API_KEY=... / GEMINI_API_KEY=...\n"
                  "  mnemo config set provider auto    # 自动挑可用后端\n"
                  "  mnemo persona use 程序员           # 选个人格\n"
                  "  mnemo                              # 开始对话"))
        return 0

    def ask(q, default=""):
        try:
            return input(cyan(q)).strip() or default
        except (EOFError, KeyboardInterrupt):
            return default

    ready = [s["name"] for s in provider_status(cfg) if s["available"] and s["name"] != "offline"]
    print(dim("检测到可用后端：" + (", ".join(ready) or "无（将用离线兜底，配置 Key 解锁全部能力）")))
    prov = ask("选择 provider（anthropic/openai/gemini/ollama/auto）[auto]：", "auto")
    cfg.set("provider", prov)
    if prov in ("anthropic", "openai", "gemini") and not cfg.get(f"providers.{prov}.api_key"):
        key = ask(f"输入 {prov} 的 API Key（留空稍后用环境变量）：")
        if key:
            cfg.set(f"providers.{prov}.api_key", key)
    personas = list((cfg.get("personas", {}) or {}).keys())
    print(dim("可选人格：" + "、".join(personas)))
    pe = ask("默认人格（留空=通用）：")
    if pe and pe in personas:
        cfg.set("persona_active", pe)
    cfg.save()
    name = ask("我该怎么称呼你？：")
    if name and cfg.get("memory.enabled", True):
        mem = Memory(cfg.db_path)
        mem.set_profile("name", name)
        mem.add_fact(f"你叫{name}", kind="identity", importance=5, source="init")
        mem.close()
    print(green("✓ 初始化完成！") + dim(" 输入 mnemo 开始对话，它会越来越懂你。"))
    return 0


def cmd_status(args):
    app = build_app(args)
    cfg = app.cfg
    print(bold("✦ Mnemo 状态"))
    p = app.provider
    print(f"  后端     {p.name}/{p.model or 'default'}")
    if app.memory:
        s = app.memory.stats()
        know = len(app.memory.facts_by(kind="knowledge", limit=100000))
        print(f"  记忆     事实 {s['facts']}（知识 {know}） · 对话 {s['episodes']} · 话题 {s['topics']}")
        prof = app.memory.profile_summary()
        if prof:
            print(dim("  画像     " + prof.replace("\n", "\n           ")))
        pend = app.memory.pending_reminders()
        if pend:
            nr = pend[0]
            when = time.strftime("%m-%d %H:%M", time.localtime(nr["remind_at"]))
            print(f"  提醒     {len(pend)} 条待办（最近 {when}：{nr['text'][:30]}）")
    try:
        from .usage import UsageStore
        us = UsageStore(cfg.db_path)
        t = us.summary(time.time() - 86400)
        us.close()
        if t["calls"]:
            line = f"  今日用量 {t['calls']} 次 · 入 {_fmt_tok(t['in_tok'])} · 出 {_fmt_tok(t['out_tok'])}"
            print(line + (f" · ${t['cost']:.4f}" if t["cost"] else ""))
    except Exception:  # noqa: BLE001
        pass
    try:
        from .daemon import TaskStore
        ts = TaskStore(cfg.db_path)
        tasks = ts.list()
        if tasks:
            print(f"  任务     {len(tasks)} 个（启用 {sum(1 for t in tasks if t.enabled)}）")
        sess = app.memory.sessions() if app.memory else []
        if sess:
            print(f"  会话     {len(sess)} 个")
    except Exception:  # noqa: BLE001
        pass
    mcp = cfg.get("mcp.servers", {}) or {}
    if mcp:
        print(f"  MCP      {len(mcp)} 个服务：{', '.join(mcp)}")
    return 0


def cmd_doctor(args):
    cfg = load_config(getattr(args, "home", None))
    print(bold("Mnemo 自检"))
    print(f"  版本      {__version__}")
    print(f"  Python    {sys.version.split()[0]}")
    print(f"  数据目录   {cfg.home}")
    print(f"  数据库     {cfg.db_path} ({'存在' if cfg.db_path.exists() else '将自动创建'})")
    print(f"  技能目录   {cfg.skills_dir}")
    print(f"  插件目录   {cfg.plugins_dir}")
    print(bold("\n大模型后端"))
    ready = False
    for st in provider_status(cfg):
        mark = green("● 就绪") if st["available"] else dim("○ 未就绪")
        ready = ready or (st["available"] and st["name"] != "offline")
        print(f"  {mark}  {st['name']} ({st.get('model')})")
    if not ready:
        print(yellow("\n提示：未检测到联网大模型，将使用离线兜底。配置 Key 解锁完整能力。"))
    try:
        m = Memory(cfg.db_path)
        s = m.stats()
        print(bold("\n记忆") + f"  事实 {s['facts']} · 对话 {s['episodes']} · 话题 {s['topics']}")
    except Exception as e:  # noqa: BLE001
        print(red(f"记忆库异常：{e}"))
    # 能力探测（不联网）
    import shutil as _sh
    from .providers import build_provider as _bp
    from .tools import _TTS
    prov = _bp(cfg)
    tts = next((c for c, _ in _TTS if _sh.which(c)), None)
    print(bold("\n能力") + f"  原生工具 {'✓' if prov.supports_tools() else '—'}  ·  "
          f"视觉 {'✓' if prov.supports_vision() else '—'}  ·  系统TTS {tts or '—'}  ·  "
          f"whisper {_sh.which('whisper') and '✓' or '—'}")
    mcp_servers = cfg.get("mcp.servers", {}) or {}
    print(bold("\nMCP") + f"  已配置 {len(mcp_servers)} 个服务" +
          (f"：{', '.join(mcp_servers)}" if mcp_servers else "（mnemo mcp add 接入）"))
    try:
        from .usage import UsageStore
        us = UsageStore(cfg.db_path)
        tot = us.summary()
        us.close()
        print(bold("\n用量") + f"  累计 {tot['calls']} 次调用 · "
              f"入 {_fmt_tok(tot['in_tok'])} · 出 {_fmt_tok(tot['out_tok'])}"
              + (f" · ${tot['cost']:.4f}" if tot['cost'] else "") + dim("（mnemo usage 看详情）"))
    except Exception:  # noqa: BLE001
        pass
    return 0


# ---------------- 解析器 ----------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mnemo",
        description="Mnemo · 本地 7×24 AI 伙伴 · 永久记忆 · 接入任意大模型 · 可学技能装插件")
    p.add_argument("--home", help="数据目录（默认 ~/.mnemo）")
    p.add_argument("--provider", help="临时指定 provider（anthropic/openai/ollama/offline/auto）")
    p.add_argument("--model", help="临时指定模型名")
    p.add_argument("-v", "--verbose", action="store_true", help="显示思考/工具细节")
    p.add_argument("--version", action="version", version=f"Mnemo {__version__}")
    sub = p.add_subparsers(dest="cmd")

    pch = sub.add_parser("chat", help="进入交互对话（默认）")
    pch.add_argument("--session", help="使用/创建指定会话名")
    pch.add_argument("--resume", action="store_true", help="续接最近一次会话")

    pr = sub.add_parser("run", help="单次执行一个任务")
    pr.add_argument("prompt", help="任务描述")
    pr.add_argument("--cwd", default=".", help="工作目录")
    pr.add_argument("--session", help="使用指定会话名")
    pr.add_argument("--json", action="store_true", help="以 JSON 输出 {reply, steps}（便于脚本）")
    pr.add_argument("--distill", metavar="NAME", help="完成后把过程沉淀为名为 NAME 的技能")

    pin = sub.add_parser("ingest", help="把本地文档/目录摄入长期记忆（知识库 RAG）")
    pin.add_argument("path", help="文件或目录")
    pin.add_argument("--tag", default="", help="给这批知识打标签，便于检索/管理")
    pin.add_argument("--max-chars", type=int, default=800, dest="max_chars", help="每块最大字符数")
    pin.add_argument("--no-embed", action="store_true", help="不计算向量（仅关键词检索）")

    pc = sub.add_parser("config", help="查看/修改配置")
    pcs = pc.add_subparsers(dest="action", required=True)
    pcs.add_parser("show"); pcs.add_parser("path")
    g = pcs.add_parser("get"); g.add_argument("key")
    s = pcs.add_parser("set"); s.add_argument("key"); s.add_argument("value")

    pp = sub.add_parser("provider", help="大模型后端")
    pps = pp.add_subparsers(dest="action", required=True)
    pps.add_parser("list"); pps.add_parser("test")

    ppe = sub.add_parser("persona", help="人格：命名切换 AI 的语气与定位")
    ppes = ppe.add_subparsers(dest="action", required=True)
    ppes.add_parser("list"); ppes.add_parser("reset")
    pesh = ppes.add_parser("show"); pesh.add_argument("name")
    pea = ppes.add_parser("add"); pea.add_argument("name"); pea.add_argument("prompt")
    peu = ppes.add_parser("use"); peu.add_argument("name")
    per = ppes.add_parser("remove"); per.add_argument("name")

    pm = sub.add_parser("memory", help="永久记忆")
    pms = pm.add_subparsers(dest="action", required=True)
    ml = pms.add_parser("list"); ml.add_argument("--limit", type=int, default=30)
    ml.add_argument("--kind"); ml.add_argument("--tag"); ml.add_argument("--source")
    msr = pms.add_parser("search"); msr.add_argument("query"); msr.add_argument("--limit", type=int, default=10)
    ma = pms.add_parser("add"); ma.add_argument("text")
    ma.add_argument("--kind", default="fact"); ma.add_argument("--importance", type=int, default=3)
    mf = pms.add_parser("forget"); mf.add_argument("id", type=int)
    mfs = pms.add_parser("forget-source", help="按来源前缀批量删除（如某次 ingest）")
    mfs.add_argument("source")
    mex = pms.add_parser("export", help="导出记忆为 Markdown")
    mex.add_argument("--out", default="mnemo-memory.md")
    mim = pms.add_parser("import", help="批量导入事实（.json 列表或每行一条的文本）")
    mim.add_argument("file")
    pms.add_parser("profile"); pms.add_parser("stats")
    pms.add_parser("consolidate", help="主动巩固：合并近重复、淡忘陈旧低价值记忆")
    pms.add_parser("backfill", help="为记忆补算语义向量（需后端支持 embed）")
    pms.add_parser("reminders", help="查看待办提醒")
    mr = pms.add_parser("remind", help="设置定时提醒")
    mr.add_argument("text"); mr.add_argument("--when", required=True,
                                             help="in 2h / 18:30 / 2026-06-17 09:00")
    mg = pms.add_parser("graph", help="导出记忆关系图为自包含 HTML")
    mg.add_argument("--out", default="mnemo-graph.html"); mg.add_argument("--limit", type=int, default=80)

    pse2 = sub.add_parser("session", help="会话：列出/查看/导出历史对话")
    pse2s = pse2.add_subparsers(dest="action", required=True)
    pse2s.add_parser("list")
    ssh2 = pse2s.add_parser("show"); ssh2.add_argument("session")
    sex2 = pse2s.add_parser("export"); sex2.add_argument("session")
    sex2.add_argument("--out", default="session.md")
    ssm2 = pse2s.add_parser("summarize", help="把较早对话压缩为滚动摘要（长会话保持连贯）")
    ssm2.add_argument("session")

    ps = sub.add_parser("skill", help="技能：学习/查看/管理")
    pss = ps.add_subparsers(dest="action", required=True)
    pss.add_parser("list")
    ssh = pss.add_parser("show"); ssh.add_argument("name")
    srn = pss.add_parser("run", help="显式用某技能完成一个任务")
    srn.add_argument("name"); srn.add_argument("input")
    sn = pss.add_parser("new"); sn.add_argument("name")
    sl = pss.add_parser("learn")
    sl.add_argument("--name"); sl.add_argument("--file"); sl.add_argument("--url"); sl.add_argument("--text")
    srm = pss.add_parser("remove"); srm.add_argument("name")
    sd = pss.add_parser("distill", help="把最近一次任务自动沉淀为新技能（自我进化）")
    sd.add_argument("--name", required=True)

    pl = sub.add_parser("plugin", help="插件：安装/管理")
    pls = pl.add_subparsers(dest="action", required=True)
    pls.add_parser("list")
    pli = pls.add_parser("install"); pli.add_argument("source")
    pli.add_argument("--name"); pli.add_argument("-y", "--yes", action="store_true")
    plr = pls.add_parser("remove"); plr.add_argument("name")

    pw = sub.add_parser("watch", help="文件监视：路径变化即触发任务（守护进程生效）")
    pws = pw.add_subparsers(dest="action", required=True)
    pws.add_parser("list")
    pwa = pws.add_parser("add")
    pwa.add_argument("--name", required=True); pwa.add_argument("--path", required=True)
    pwa.add_argument("--prompt", required=True)
    pwr = pws.add_parser("remove"); pwr.add_argument("name")

    pmc = sub.add_parser("mcp", help="MCP：接入任意 Model Context Protocol 服务的工具")
    pmcs = pmc.add_subparsers(dest="action", required=True)
    pmcs.add_parser("list")
    mca = pmcs.add_parser("add", help="添加一个 MCP 服务到配置")
    mca.add_argument("name")
    mca.add_argument("--command", required=True, help="启动命令，如 npx / uvx / python")
    mca.add_argument("--arg", action="append", help="命令参数（可多次）")
    mca.add_argument("--env", action="append", help="环境变量 K=V（可多次）")
    mcr = pmcs.add_parser("remove"); mcr.add_argument("name")
    mct = pmcs.add_parser("test", help="连接某服务并列出其工具"); mct.add_argument("name")

    pt = sub.add_parser("task", help="7×24 定时任务")
    pts = pt.add_subparsers(dest="action", required=True)
    ta = pts.add_parser("add")
    ta.add_argument("--name", required=True)
    ta.add_argument("--every", required=True, help="调度：every 30m / @hourly / @daily 09:00 / @startup")
    ta.add_argument("--prompt", required=True)
    pts.add_parser("list")
    th = pts.add_parser("history", help="查看任务执行历史")
    th.add_argument("id", type=int, nargs="?"); th.add_argument("--limit", type=int, default=30)
    trm = pts.add_parser("rm"); trm.add_argument("id", type=int)
    te = pts.add_parser("enable"); te.add_argument("id", type=int)
    td = pts.add_parser("disable"); td.add_argument("id", type=int)
    trn = pts.add_parser("run"); trn.add_argument("id", type=int)

    pd = sub.add_parser("daemon", help="启动守护进程，后台跑任务")
    pd.add_argument("--once", action="store_true", help="只巡检一次（用于测试/cron）")
    pd.add_argument("--interval", type=int, default=30, help="巡检间隔秒")
    pd.add_argument("--status", action="store_true", help="查看守护进程是否在运行")
    pd.add_argument("--stop", action="store_true", help="停止正在运行的守护进程")

    pa = sub.add_parser("audit", help="查看工具调用审计日志")
    pa.add_argument("--limit", type=int, default=30)

    sub.add_parser("usage", help="查看 token 用量与成本（今日/7天/累计/按模型）")

    pmk = sub.add_parser("market", help="技能/插件市场：搜索/安装/签名/评分")
    pmk.add_argument("--registry", help="registry 文件或 URL（默认读 config.registry）")
    pmk.add_argument("--key", help="签名校验/签名用的密钥（或 config.registry_key）")
    pmks = pmk.add_subparsers(dest="action", required=True)
    pmks.add_parser("list")
    mks = pmks.add_parser("search"); mks.add_argument("query")
    mki = pmks.add_parser("install"); mki.add_argument("name")
    mki.add_argument("-y", "--yes", action="store_true", help="跳过插件安装确认")
    pmks.add_parser("verify", help="校验 registry 签名")
    msg = pmks.add_parser("sign", help="给 registry 签名"); msg.add_argument("--out")
    mra = pmks.add_parser("rate", help="给某技能/插件本地评分")
    mra.add_argument("name"); mra.add_argument("stars", type=int)
    mra.add_argument("--note", default="")

    psy = sub.add_parser("sync", help="跨设备记忆同步：加密导出/导入")
    psys = psy.add_subparsers(dest="action", required=True)
    se = psys.add_parser("export"); se.add_argument("file"); se.add_argument("--passphrase")
    si = psys.add_parser("import"); si.add_argument("file"); si.add_argument("--passphrase")

    psv = sub.add_parser("serve", help="启动本地 Web 图形界面（手机/电脑浏览器可用）")
    psv.add_argument("--host", default="127.0.0.1", help="0.0.0.0 可供局域网团队共享")
    psv.add_argument("--port", type=int, default=8765)
    psv.add_argument("--token", help="访问令牌（局域网共享时强烈建议设置）")

    psp = sub.add_parser("speak", help="用系统 TTS 朗读一段文本（语音输出）")
    psp.add_argument("text")
    pse = sub.add_parser("see", help="用视觉模型理解图片或视频（多模态，视频需 ffmpeg）")
    pse.add_argument("path"); pse.add_argument("--prompt", default="详细描述这张图片")

    pvo = sub.add_parser("voice", help="语音对话：录音→转写→回答→朗读")
    pvo.add_argument("--seconds", type=int, default=5); pvo.add_argument("--once", action="store_true")

    pn = sub.add_parser("notify", help="推送一条通知（测试 desktop/webhook 渠道）")
    pn.add_argument("message"); pn.add_argument("--title", default="Mnemo")

    sub.add_parser("init", help="初始化向导：选后端/人格/称呼")
    sub.add_parser("status", help="一览：后端/记忆/用量/提醒/任务/会话/MCP")
    sub.add_parser("doctor", help="环境自检")
    return p


_HANDLERS = {
    "chat": cmd_chat, "run": cmd_run, "ingest": cmd_ingest, "config": cmd_config,
    "provider": cmd_provider, "persona": cmd_persona,
    "memory": cmd_memory, "session": cmd_session, "skill": cmd_skill,
    "plugin": cmd_plugin, "task": cmd_task, "watch": cmd_watch,
    "daemon": cmd_daemon, "doctor": cmd_doctor, "init": cmd_init, "status": cmd_status,
    "notify": cmd_notify, "audit": cmd_audit,
    "market": cmd_market, "sync": cmd_sync, "speak": cmd_speak, "see": cmd_see,
    "serve": cmd_serve, "voice": cmd_voice, "mcp": cmd_mcp, "usage": cmd_usage,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.cmd:
        args.cmd = "chat"
    handler = _HANDLERS[args.cmd]
    try:
        return handler(args) or 0
    except KeyboardInterrupt:
        print("\n已中断")
        return 130


if __name__ == "__main__":
    sys.exit(main())
