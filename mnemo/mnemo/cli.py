"""Mnemo 命令行入口：把 provider / 记忆 / 工具 / 技能 / 插件 / 守护进程串起来。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass

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


def build_app(args) -> App:
    cfg = load_config(getattr(args, "home", None))
    if getattr(args, "provider", None):
        cfg.set("provider", args.provider)
    if getattr(args, "model", None):
        cfg.set("model", args.model)
    memory = Memory(cfg.db_path) if cfg.get("memory.enabled", True) else None
    tools = build_default_registry()
    skills = SkillRegistry(cfg)
    plugins = PluginManager(cfg, tools, skills)
    plugins.load_all()
    provider = build_provider(cfg)
    agent = Agent(provider, tools, memory, skills, cfg)
    return App(cfg, provider, memory, tools, skills, plugins, agent)


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
    app = build_app(args)
    p = app.provider
    print(bold("✦ Mnemo") + dim(f"  {p.name}/{p.model or 'default'}  ·  /help 命令  ·  /exit 退出"))
    if app.memory:
        prof = app.memory.profile_summary()
        if prof:
            print(dim("我对你的了解：\n" + prof))
    on_event = _make_on_event(args.verbose)
    session = "default"
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
            print(dim("/memory 记忆概览  /profile 画像  /skills 技能  /provider 后端  "
                      "/forget <id> 删记忆  /distill <名> 把刚才任务存为技能  "
                      "/new 新会话  /exit 退出"))
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
        try:
            reply = app.agent.run(line, session=session, on_event=on_event,
                                   auto_approve=not confirm_danger, confirm=_confirm)
            print(bold("Mnemo › ") + reply)
        except ProviderError as e:
            print(red(f"[模型调用失败] {e}"))


def cmd_run(args):
    app = build_app(args)
    try:
        out = app.agent.run(args.prompt, cwd=args.cwd,
                            on_event=_make_on_event(args.verbose))
    except ProviderError as e:
        print(red(f"[模型调用失败] {e}"), file=sys.stderr)
        return 1
    print(out)
    if getattr(args, "distill", None):
        from .skills import distill_from_trace
        text = distill_from_trace(app.agent.last_trace, app.provider, args.distill)
        s = app.skills.learn(name=args.distill, text=text)
        print(dim(f"✦ 已把本次过程沉淀为技能：{s.name}"), file=sys.stderr)
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


def cmd_provider(args):
    cfg = load_config(getattr(args, "home", None))
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
        for f in m.all_facts(limit=args.limit):
            print(f"#{f['id']:<4} [{f['kind']}] 重要度{f['importance']}  {f['text']}")
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


def cmd_task(args):
    app = build_app(args)
    from .daemon import TaskStore
    store = TaskStore(app.cfg.db_path)
    if args.action == "add":
        tid = store.add(args.name, args.prompt, args.every)
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


def cmd_daemon(args):
    app = build_app(args)
    from .daemon import Scheduler, TaskStore
    store = TaskStore(app.cfg.db_path)
    sched = Scheduler(app.agent, store)
    if args.once:
        n = sched.run_once()
        print(dim(f"本轮执行了 {n} 个到期任务"))
    else:
        sched.serve(interval=args.interval)
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

    sub.add_parser("chat", help="进入交互对话（默认）")

    pr = sub.add_parser("run", help="单次执行一个任务")
    pr.add_argument("prompt", help="任务描述")
    pr.add_argument("--cwd", default=".", help="工作目录")
    pr.add_argument("--distill", metavar="NAME", help="完成后把过程沉淀为名为 NAME 的技能")

    pc = sub.add_parser("config", help="查看/修改配置")
    pcs = pc.add_subparsers(dest="action", required=True)
    pcs.add_parser("show"); pcs.add_parser("path")
    g = pcs.add_parser("get"); g.add_argument("key")
    s = pcs.add_parser("set"); s.add_argument("key"); s.add_argument("value")

    pp = sub.add_parser("provider", help="大模型后端")
    pps = pp.add_subparsers(dest="action", required=True)
    pps.add_parser("list"); pps.add_parser("test")

    pm = sub.add_parser("memory", help="永久记忆")
    pms = pm.add_subparsers(dest="action", required=True)
    ml = pms.add_parser("list"); ml.add_argument("--limit", type=int, default=30)
    msr = pms.add_parser("search"); msr.add_argument("query"); msr.add_argument("--limit", type=int, default=10)
    ma = pms.add_parser("add"); ma.add_argument("text")
    ma.add_argument("--kind", default="fact"); ma.add_argument("--importance", type=int, default=3)
    mf = pms.add_parser("forget"); mf.add_argument("id", type=int)
    pms.add_parser("profile"); pms.add_parser("stats")
    pms.add_parser("consolidate", help="主动巩固：合并近重复、淡忘陈旧低价值记忆")
    pms.add_parser("backfill", help="为记忆补算语义向量（需后端支持 embed）")
    pms.add_parser("reminders", help="查看待办提醒")
    mr = pms.add_parser("remind", help="设置定时提醒")
    mr.add_argument("text"); mr.add_argument("--when", required=True,
                                             help="in 2h / 18:30 / 2026-06-17 09:00")

    ps = sub.add_parser("skill", help="技能：学习/查看/管理")
    pss = ps.add_subparsers(dest="action", required=True)
    pss.add_parser("list")
    ssh = pss.add_parser("show"); ssh.add_argument("name")
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

    pt = sub.add_parser("task", help="7×24 定时任务")
    pts = pt.add_subparsers(dest="action", required=True)
    ta = pts.add_parser("add")
    ta.add_argument("--name", required=True)
    ta.add_argument("--every", required=True, help="调度：every 30m / @hourly / @daily 09:00 / @startup")
    ta.add_argument("--prompt", required=True)
    pts.add_parser("list")
    trm = pts.add_parser("rm"); trm.add_argument("id", type=int)
    te = pts.add_parser("enable"); te.add_argument("id", type=int)
    td = pts.add_parser("disable"); td.add_argument("id", type=int)
    trn = pts.add_parser("run"); trn.add_argument("id", type=int)

    pd = sub.add_parser("daemon", help="启动守护进程，后台跑任务")
    pd.add_argument("--once", action="store_true", help="只巡检一次（用于测试/cron）")
    pd.add_argument("--interval", type=int, default=30, help="巡检间隔秒")

    pa = sub.add_parser("audit", help="查看工具调用审计日志")
    pa.add_argument("--limit", type=int, default=30)

    sub.add_parser("doctor", help="环境自检")
    return p


_HANDLERS = {
    "chat": cmd_chat, "run": cmd_run, "config": cmd_config, "provider": cmd_provider,
    "memory": cmd_memory, "skill": cmd_skill, "plugin": cmd_plugin, "task": cmd_task,
    "daemon": cmd_daemon, "doctor": cmd_doctor, "audit": cmd_audit,
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
