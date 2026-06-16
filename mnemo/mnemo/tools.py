"""工具系统：Agent 通过通用文本协议调用这些工具与真实世界交互。

插件可调用 registry.register() 注入新工具，实现能力无限扩展。
"""
from __future__ import annotations

import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

# 明显高危、直接拒绝执行的 shell 模式（防误伤，非完整沙箱）
_SHELL_DENY = [
    r"rm\s+-rf\s+/(?:\s|$)", r":\(\)\s*\{", r"mkfs", r"\bdd\s+if=",
    r">\s*/dev/sd", r"chmod\s+-R\s+777\s+/", r"\bshutdown\b", r"\breboot\b",
]


@dataclass
class ToolContext:
    """工具运行时上下文。"""
    memory: object = None
    config: object = None
    cwd: str = "."
    auto_approve: bool = True   # daemon/非交互下自动放行；交互模式可由 CLI 改写
    confirm: Callable[[str], bool] | None = None
    agent: object = None        # 当前 Agent（供 delegate 派生子 Agent）


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict          # 参数名 -> 说明
    func: Callable            # (args: dict, ctx: ToolContext) -> str
    danger: bool = False      # 是否需要确认（写入/执行类）

    def spec(self) -> str:
        params = ", ".join(f"{k}（{v}）" for k, v in self.parameters.items()) or "无"
        flag = " ⚠需确认" if self.danger else ""
        return f"- {self.name}: {self.description}{flag}\n  参数: {params}"


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def add(self, name, description, parameters, func, danger=False) -> None:
        self.register(Tool(name, description, parameters, func, danger))

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def specs(self) -> str:
        return "\n".join(t.spec() for t in self._tools.values())

    def run(self, name: str, args: dict, ctx: ToolContext) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"[错误] 未知工具：{name}。可用：{', '.join(self.names())}"
        if tool.danger and not ctx.auto_approve:
            ok = ctx.confirm(f"执行高危工具 {name}({args})？") if ctx.confirm else False
            if not ok:
                return f"[已取消] 用户拒绝执行 {name}"
        try:
            return tool.func(args or {}, ctx)
        except Exception as e:  # noqa: BLE001
            return f"[工具异常] {name}: {e}"


# ---------------- 内置工具实现 ----------------

def _t_read_file(args, ctx):
    path = Path(ctx.cwd) / args["path"]
    if not path.is_file():
        return f"[错误] 文件不存在：{path}"
    data = path.read_text(encoding="utf-8", errors="replace")
    return data[:20000] + ("\n…(已截断)" if len(data) > 20000 else "")


def _t_write_file(args, ctx):
    path = Path(ctx.cwd) / args["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args.get("content", ""), encoding="utf-8")
    return f"已写入 {path}（{len(args.get('content', ''))} 字符）"


def _t_list_dir(args, ctx):
    path = Path(ctx.cwd) / args.get("path", ".")
    if not path.is_dir():
        return f"[错误] 目录不存在：{path}"
    items = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
    return "\n".join(items[:200]) or "(空目录)"


def _t_run_shell(args, ctx):
    cmd = args.get("command", "")
    if ctx.config and not ctx.config.get("allow_shell", True):
        return "[已禁用] 配置 allow_shell=false，已拒绝执行 shell。"
    for pat in _SHELL_DENY:
        if re.search(pat, cmd):
            return f"[已拦截] 命令命中高危模式，拒绝执行：{pat}"
    timeout = int(ctx.config.get("shell_timeout", 60)) if ctx.config else 60
    try:
        r = subprocess.run(cmd, shell=True, cwd=ctx.cwd, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"[超时] 命令超过 {timeout}s 被终止"
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    out = out.strip() or "(无输出)"
    return f"[退出码 {r.returncode}]\n{out[:8000]}"


def _t_web_fetch(args, ctx):
    url = args["url"]
    if not re.match(r"^https?://", url):
        return "[错误] 仅支持 http(s) URL"
    req = urllib.request.Request(url, headers={"User-Agent": "Mnemo/0.1"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read(2_000_000).decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:6000] + ("\n…(已截断)" if len(text) > 6000 else "")


def _t_remember(args, ctx):
    if not ctx.memory:
        return "[错误] 记忆不可用"
    fid = ctx.memory.add_fact(args["text"], kind=args.get("kind", "fact"),
                              importance=int(args.get("importance", 3)), source="tool")
    return f"已记住（#{fid}）：{args['text']}"


def _t_recall(args, ctx):
    if not ctx.memory:
        return "[错误] 记忆不可用"
    hits = ctx.memory.recall(args["query"], limit=int(args.get("limit", 6)))
    if not hits:
        return "(没有相关记忆)"
    return "\n".join(f"- {h['text']}" for h in hits)


def _t_now(args, ctx):
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")


def _t_delegate(args, ctx):
    """把一个聚焦的子任务委派给子 Agent（多 Agent 协作），返回其结果。"""
    parent = ctx.agent
    if parent is None or not hasattr(parent, "_make_subagent"):
        return "[delegate] 当前环境不支持委派"
    if getattr(parent, "_depth", 0) >= 2:
        return "[delegate] 已达最大委派深度（防止无限递归）"
    sub = parent._make_subagent()
    role = args.get("role", "专家助手")
    task = args.get("task", "")
    out = sub.run(f"你的角色是「{role}」。聚焦完成这个子任务，直接给结论：\n{task}",
                  session="subagent", cwd=ctx.cwd, auto_approve=ctx.auto_approve)
    return f"[{role} 的结果]\n{out}"[:2500]


def _t_remind(args, ctx):
    if not ctx.memory:
        return "[错误] 记忆不可用"
    from .memory import parse_when
    when = parse_when(args.get("when", ""))
    if when is None:
        return "[错误] 无法解析时间，请用：in 2h / 18:30 / 2026-06-17 09:00"
    import time
    rid = ctx.memory.add_reminder(args["text"], when)
    return f"已设提醒 #{rid}：{args['text']}（{time.strftime('%m-%d %H:%M', time.localtime(when))}）"


def build_default_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.add("read_file", "读取文本文件内容", {"path": "相对/绝对路径"}, _t_read_file)
    r.add("write_file", "写入/覆盖文本文件", {"path": "路径", "content": "内容"},
          _t_write_file, danger=True)
    r.add("list_dir", "列出目录内容", {"path": "目录，默认当前"}, _t_list_dir)
    r.add("run_shell", "执行 shell 命令并返回输出", {"command": "命令"},
          _t_run_shell, danger=True)
    r.add("web_fetch", "抓取网页并返回纯文本", {"url": "http(s) 链接"}, _t_web_fetch)
    r.add("remember", "把一条信息写入长期记忆",
          {"text": "要记住的内容", "importance": "1-5，默认3"}, _t_remember)
    r.add("recall", "从长期记忆检索", {"query": "查询词", "limit": "条数"}, _t_recall)
    r.add("now", "获取当前日期时间", {}, _t_now)
    r.add("remind", "设置一个定时提醒（守护进程到点会主动触发）",
          {"text": "提醒内容", "when": "时间：in 2h / 18:30 / 2026-06-17 09:00"}, _t_remind)
    r.add("delegate", "把一个聚焦子任务交给子 Agent 处理并拿回结果（多 Agent 协作）",
          {"role": "子 Agent 的角色，如 研究员/程序员/审阅者", "task": "子任务描述"},
          _t_delegate)
    return r
