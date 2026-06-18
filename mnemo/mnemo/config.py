"""配置管理：默认值 + 用户配置文件 + 环境变量 + 项目级 .env，分层合并。

优先级（高 → 低）：环境变量 > 项目 .mnemo.json > 用户 config.json > 内置默认。
密钥优先从环境变量读取（更安全），也允许写在 config.json 里。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    # provider=auto 时按可用性自动挑选：anthropic → openai → ollama → offline
    "provider": "auto",
    "model": None,            # 留空则用所选 provider 的默认模型
    "temperature": 0.7,
    "max_tokens": 2048,
    "max_steps": 8,           # 单次任务里工具调用的最大轮数
    "allow_shell": True,      # 是否允许 run_shell 工具
    "shell_timeout": 60,
    "persona": "你是 Mnemo，用户的私人 AI 伙伴：可靠、简洁、主动。说中文。",
    # 人格：可命名切换；persona_active 指向 personas 里的某个，留空则用上面的 persona
    "persona_active": None,
    "personas": {
        "程序员": "你是资深工程师：给出可运行代码与简洁解释，重视边界、安全与可维护性。说中文。",
        "教练": "你是耐心的成长教练：多问启发式问题，鼓励用户，给可执行的小步骤。说中文。",
        "研究员": "你是严谨的研究员：先列要点再展开，标注不确定与来源，不臆断。说中文。",
    },
    "native_tools": False,    # true 时对支持的后端启用原生 function-calling（更稳）
    "registry": "",           # 技能/插件市场地址（本地文件或 URL）
    "memory": {"enabled": True, "recall_limit": 6, "min_importance": 1, "semantic": False},
    "ui": {"stream": True},   # 交互对话逐字流式输出（终端可见时生效）
    # 通知推送：让到点提醒/任务结果触达用户（desktop / webhook / email / 兜底 stdout）
    "notify": {"channel": "auto", "webhook": "", "on_reminder": True, "on_task": False,
               "email": {"smtp_host": "", "port": 587, "user": "", "password": "",
                         "to": "", "from": "", "starttls": True}},
    # 用量观测：记录每次模型调用的 token；pricing 可选（每百万 token 单价）才算成本
    # daily_token_limit>0 时，今日用量达上限即暂停调用（无人值守的成本护栏）
    "usage": {"enabled": True, "daily_token_limit": 0},
    "pricing": {},            # 例：{"gpt-4o-mini": {"in": 0.15, "out": 0.6}}
    # 安全：confirm_danger 在交互模式下让写入/执行类工具需确认；deny 永久禁用某些工具
    "tools": {"confirm_danger": False, "deny": []},
    # 沙箱：engine=docker/podman 时 run_shell 在容器内隔离执行（--network none）
    "sandbox": {"engine": "none", "image": "python:3.11-slim"},
    # 文件监视：路径变化即触发 prompt（守护进程巡检）。每项 {name, path, prompt}
    "watch": [],
    # MCP：接入任意 Model Context Protocol 服务，把其工具并入 Mnemo
    # servers 形如 {"名字": {"command": "npx", "args": [...], "env": {...}}}
    "mcp": {"servers": {}},
    "providers": {
        "anthropic": {"model": "claude-opus-4-8", "base_url": "https://api.anthropic.com"},
        "openai": {"model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"},
        "gemini": {"model": "gemini-2.0-flash",
                   "base_url": "https://generativelanguage.googleapis.com/v1beta"},
        "ollama": {"model": "llama3.1", "base_url": "http://localhost:11434"},
    },
}

# 环境变量 → 配置路径 的映射（点路径）
ENV_MAP = {
    "MNEMO_PROVIDER": "provider",
    "MNEMO_MODEL": "model",
    "ANTHROPIC_API_KEY": "providers.anthropic.api_key",
    "ANTHROPIC_BASE_URL": "providers.anthropic.base_url",
    "OPENAI_API_KEY": "providers.openai.api_key",
    "OPENAI_BASE_URL": "providers.openai.base_url",
    "OPENAI_MODEL": "providers.openai.model",
    "GEMINI_API_KEY": "providers.gemini.api_key",
    "GOOGLE_API_KEY": "providers.gemini.api_key",
    "GEMINI_MODEL": "providers.gemini.model",
    "OLLAMA_BASE_URL": "providers.ollama.base_url",
    "OLLAMA_MODEL": "providers.ollama.model",
}


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_dotenv(path: Path) -> None:
    """把 .env 里未在环境中存在的键载入 os.environ（不覆盖已有）。"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


class Config:
    def __init__(self, data: dict, home: Path):
        self.data = data
        self.home = home
        self._env_paths: set[str] = set()   # 从环境注入的路径，save 时不落盘

    # ---- 路径 ----
    @property
    def db_path(self) -> Path:
        return self.home / "mnemo.db"

    @property
    def skills_dir(self) -> Path:
        return self.home / "skills"

    @property
    def plugins_dir(self) -> Path:
        return self.home / "plugins"

    @property
    def config_file(self) -> Path:
        return self.home / "config.json"

    # ---- 读写 ----
    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def set(self, path: str, value: Any) -> None:
        self._env_paths.discard(path)   # 用户显式设置 → 视为可持久化
        parts = path.split(".")
        cur = self.data
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
            if not isinstance(cur, dict):
                raise ValueError(f"配置路径冲突：{path}")
        cur[parts[-1]] = value

    def save(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        # 不把从环境注入的密钥写回磁盘：env 提供的值仅在内存生效，下次加载会再注入。
        import copy
        out = copy.deepcopy(self.data)
        for path in self._env_paths:
            cur = out
            parts = path.split(".")
            for p in parts[:-1]:
                if not isinstance(cur, dict) or p not in cur:
                    cur = None
                    break
                cur = cur[p]
            if isinstance(cur, dict):
                cur.pop(parts[-1], None)
        self.config_file.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def provider_conf(self, name: str) -> dict:
        return dict(self.get(f"providers.{name}", {}) or {})


def load_config(home: str | None = None) -> Config:
    home_path = Path(home or os.environ.get("MNEMO_HOME", "~/.mnemo")).expanduser()
    home_path.mkdir(parents=True, exist_ok=True)

    # .env：先项目目录，后家目录（项目优先，因先载入且不覆盖）
    _load_dotenv(Path.cwd() / ".env")
    _load_dotenv(home_path / ".env")

    data = json.loads(json.dumps(DEFAULTS))  # 深拷贝默认

    cfg_file = home_path / "config.json"
    if cfg_file.is_file():
        try:
            data = _deep_merge(data, json.loads(cfg_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass

    proj = Path.cwd() / ".mnemo.json"
    if proj.is_file():
        try:
            data = _deep_merge(data, json.loads(proj.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass

    cfg = Config(data, home_path)

    # 环境变量覆盖（最高优先级）；记录这些路径，save 时不落盘
    injected: set[str] = set()
    for env_key, path in ENV_MAP.items():
        if env_key in os.environ and os.environ[env_key]:
            cfg.set(path, os.environ[env_key])
            injected.add(path)
    cfg._env_paths = injected

    return cfg
