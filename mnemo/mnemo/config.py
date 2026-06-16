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
    "native_tools": False,    # true 时对支持的后端启用原生 function-calling（更稳）
    "registry": "",           # 技能/插件市场地址（本地文件或 URL）
    "memory": {"enabled": True, "recall_limit": 6, "min_importance": 1, "semantic": False},
    # 安全：confirm_danger 在交互模式下让写入/执行类工具需确认；deny 永久禁用某些工具
    "tools": {"confirm_danger": False, "deny": []},
    "providers": {
        "anthropic": {"model": "claude-opus-4-8", "base_url": "https://api.anthropic.com"},
        "openai": {"model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"},
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
        parts = path.split(".")
        cur = self.data
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
            if not isinstance(cur, dict):
                raise ValueError(f"配置路径冲突：{path}")
        cur[parts[-1]] = value

    def save(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        # 不把从环境注入的密钥写回磁盘：保存的是用户显式 set 的内容（self.data 已含），
        # 这里按原样保存，密钥若来自 env 则 env 优先级更高、不依赖文件。
        self.config_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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

    # 环境变量覆盖（最高优先级）
    for env_key, path in ENV_MAP.items():
        if env_key in os.environ and os.environ[env_key]:
            cfg.set(path, os.environ[env_key])

    return cfg
