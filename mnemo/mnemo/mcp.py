"""MCP（Model Context Protocol）客户端：把任意 MCP 服务的工具接进 Mnemo。

MCP 是被 Claude Desktop / Cursor 等广泛采用的工具协议，生态里已有大量现成服务
（文件系统、网页搜索、GitHub、数据库……）。Mnemo 作为 MCP 客户端，启动这些服务为
子进程，用 JSON-RPC 2.0 over stdio 通信，把它们的工具动态注册进 ToolRegistry——
于是「接入任何工具」从插件扩展到整个 MCP 生态。纯标准库，零第三方依赖。

配置（~/.mnemo/config.json）：
  "mcp": {"servers": {
     "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"]},
     "fetch":      {"command": "uvx", "args": ["mcp-server-fetch"]}
  }}

注册后的工具名形如 `filesystem.read_file`，与内置工具共用同一套文本/原生协议。
⚠ 安全：MCP 服务是外部进程、能产生副作用，默认按"高危工具"对待（受 confirm_danger 约束）。
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections import deque


class MCPError(Exception):
    """MCP 通信 / 协议 / 进程错误。"""


def _params_from_schema(schema: dict | None) -> dict:
    """把 JSON Schema 的 inputSchema 转成 Mnemo 的 {参数名: 说明} 形式。"""
    schema = schema or {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    out: dict[str, str] = {}
    for key, spec in props.items():
        spec = spec if isinstance(spec, dict) else {}
        desc = spec.get("description") or spec.get("type") or "参数"
        if key in required:
            desc = f"{desc}（必填）"
        out[key] = desc
    return out


class MCPClient:
    """单个 MCP 服务的 stdio JSON-RPC 客户端。

    生命周期：start()（拉起子进程 + initialize 握手）→ list_tools()/call_tool()
    → close()。读取用后台线程 + 队列，避免阻塞并支持超时。
    """

    PROTOCOL = "2024-11-05"  # 广泛支持的基线版本；服务会回应其实际采用的版本

    def __init__(self, name: str, command: str, args: list[str] | None = None,
                 env: dict | None = None, cwd: str | None = None, timeout: int = 30):
        self.name = name
        self.command = command
        self.args = list(args or [])
        self.env = env or {}
        self.cwd = cwd
        self.timeout = timeout
        self.proc: subprocess.Popen | None = None
        self._q: "queue.Queue[dict | None]" = queue.Queue()
        self._stderr: deque[str] = deque(maxlen=50)
        self._id = 0
        self._send_lock = threading.Lock()
        self.tools: list[dict] = []
        self.server_info: dict = {}

    # ---- 进程与 IO ----
    def start(self) -> "MCPClient":
        exe = shutil.which(self.command) or self.command
        env = dict(os.environ)
        env.update({k: str(v) for k, v in self.env.items()})
        try:
            self.proc = subprocess.Popen(
                [exe, *self.args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=env, cwd=self.cwd, text=True, bufsize=1)
        except (FileNotFoundError, OSError) as e:
            raise MCPError(f"无法启动 MCP 服务 {self.name}（{self.command}）：{e}") from e
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        init = self._request("initialize", {
            "protocolVersion": self.PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "mnemo", "version": "0.1.0"},
        })
        self.server_info = init.get("serverInfo", {}) if isinstance(init, dict) else {}
        self._notify("notifications/initialized", {})
        return self

    def _read_loop(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except json.JSONDecodeError:
                continue  # 非协议输出（部分服务会打印 banner），忽略
        self._q.put(None)  # EOF 哨兵

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self._stderr.append(line.rstrip())

    def stderr_tail(self, n: int = 8) -> str:
        return "\n".join(list(self._stderr)[-n:])

    # ---- JSON-RPC ----
    def _send(self, obj: dict) -> None:
        if not self.proc or self.proc.poll() is not None:
            raise MCPError(f"MCP 服务 {self.name} 未运行")
        with self._send_lock:
            assert self.proc.stdin
            self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()

    def _notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict) -> dict:
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.time() + self.timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise MCPError(f"{self.name} 调用 {method} 超时（{self.timeout}s）")
            try:
                msg = self._q.get(timeout=remaining)
            except queue.Empty:
                raise MCPError(f"{self.name} 调用 {method} 超时（{self.timeout}s）")
            if msg is None:
                tail = self.stderr_tail()
                raise MCPError(f"{self.name} 进程已退出" + (f"：\n{tail}" if tail else ""))
            if msg.get("id") != rid:
                continue  # 其它响应 / 通知，跳过
            if "error" in msg:
                err = msg["error"]
                raise MCPError(f"{self.name} {method} 失败：{err.get('message', err)}")
            return msg.get("result", {}) or {}

    # ---- 高层能力 ----
    def list_tools(self) -> list[dict]:
        res = self._request("tools/list", {})
        self.tools = res.get("tools", []) if isinstance(res, dict) else []
        return self.tools

    def call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        res = self._request("tools/call", {"name": tool_name, "arguments": arguments or {}})
        parts: list[str] = []
        for block in (res.get("content") or []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "resource":
                r = block.get("resource", {})
                parts.append(r.get("text") or r.get("uri", ""))
            else:
                parts.append(json.dumps(block, ensure_ascii=False))
        text = "\n".join(p for p in parts if p).strip() or "(无输出)"
        return f"[MCP错误] {text}" if res.get("isError") else text

    def close(self) -> None:
        if not self.proc:
            return
        if self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    self.proc.kill()
                except Exception:  # noqa: BLE001
                    pass
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:  # noqa: BLE001
                pass


def _make_caller(client: MCPClient, tool_name: str):
    def _call(args, ctx):
        return client.call_tool(tool_name, args or {})
    return _call


class MCPManager:
    """读取配置里的 mcp.servers，统一连接、注册工具、管理生命周期。"""

    def __init__(self, config):
        self.config = config
        self.clients: dict[str, MCPClient] = {}
        self.errors: dict[str, str] = {}
        self._atexit_armed = False

    def _server_specs(self) -> dict:
        spec = self.config.get("mcp.servers", {}) if self.config else {}
        return spec if isinstance(spec, dict) else {}

    def connect_all(self, registry) -> dict:
        """连接所有配置的服务并把工具注册进 registry。返回 {server: 工具数}。"""
        result: dict[str, int] = {}
        for name, spec in self._server_specs().items():
            if not isinstance(spec, dict) or not spec.get("command"):
                self.errors[name] = "配置缺少 command"
                continue
            try:
                count = self._connect_one(name, spec, registry)
                result[name] = count
            except MCPError as e:
                self.errors[name] = str(e)
            except Exception as e:  # noqa: BLE001
                self.errors[name] = f"{type(e).__name__}: {e}"
        if self.clients and not self._atexit_armed:
            import atexit
            atexit.register(self.close_all)
            self._atexit_armed = True
        return result

    def _connect_one(self, name: str, spec: dict, registry) -> int:
        client = MCPClient(
            name, spec["command"], spec.get("args"), spec.get("env"),
            spec.get("cwd"), int(spec.get("timeout", 30)))
        client.start()
        tools = client.list_tools()
        for t in tools:
            tname = t.get("name")
            if not tname:
                continue
            registry.add(
                f"{name}.{tname}",
                f"[MCP:{name}] " + (t.get("description") or tname),
                _params_from_schema(t.get("inputSchema")),
                _make_caller(client, tname),
                danger=True,  # 外部服务有副作用，按高危对待
            )
        self.clients[name] = client
        return len(tools)

    def probe(self, name: str) -> dict:
        """单独连接一个服务并返回其工具清单（用于 `mcp test`），随后关闭。"""
        spec = self._server_specs().get(name)
        if not spec:
            raise MCPError(f"未配置 MCP 服务：{name}")
        client = MCPClient(
            name, spec["command"], spec.get("args"), spec.get("env"),
            spec.get("cwd"), int(spec.get("timeout", 30)))
        try:
            client.start()
            tools = client.list_tools()
            return {"server_info": client.server_info, "tools": tools}
        finally:
            client.close()

    def close_all(self) -> None:
        for client in self.clients.values():
            client.close()
        self.clients.clear()
