"""插件系统：从本地路径或 git 安装，可注入工具 / 技能 / Provider。

插件目录结构：
  <plugins_dir>/<name>/
    plugin.json        # 必需：{name, version, description, entry?}
    entry.py           # 可选：定义 register(ctx) 钩子
    skills/*.md        # 可选：随插件分发的技能

entry.py 里的 register(ctx) 会在加载时被调用，ctx 提供：
  ctx.tools     —— ToolRegistry，可 .add(...) 新工具
  ctx.skills    —— SkillRegistry，可 .add_runtime(Skill(...))
  ctx.register_provider(name, cls) —— 接入新大模型后端
  ctx.config    —— 配置

⚠ 安全：插件会执行任意代码，仅安装可信来源。CLI 安装时会二次确认。
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .providers import register_provider
from .skills import _parse_skill


@dataclass
class PluginContext:
    tools: object
    skills: object
    config: object
    register_provider: object


class PluginManager:
    def __init__(self, config, tools, skills):
        self.config = config
        self.tools = tools
        self.skills = skills
        self.dir = Path(config.plugins_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.loaded: dict[str, dict] = {}
        self.errors: dict[str, str] = {}

    def _manifest(self, pdir: Path) -> dict | None:
        mf = pdir / "plugin.json"
        if not mf.is_file():
            return None
        try:
            return json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def list(self) -> list[dict]:
        out = []
        for d in sorted(self.dir.iterdir()) if self.dir.is_dir() else []:
            if not d.is_dir():
                continue
            mf = self._manifest(d) or {"name": d.name, "description": "(缺少 plugin.json)"}
            mf["_loaded"] = d.name in self.loaded
            if d.name in self.errors:
                mf["_error"] = self.errors[d.name]
            out.append(mf)
        return out

    def load_all(self) -> None:
        if not self.dir.is_dir():
            return
        for d in sorted(self.dir.iterdir()):
            if d.is_dir() and self._manifest(d):
                self._load_one(d)

    def _load_one(self, pdir: Path) -> None:
        mf = self._manifest(pdir)
        if not mf:
            return
        name = mf.get("name", pdir.name)
        try:
            # 1) 随插件分发的技能
            for sf in (pdir / "skills").glob("*.md") if (pdir / "skills").is_dir() else []:
                sk = _parse_skill(sf.read_text(encoding="utf-8"), sf)
                self.skills.add_runtime(sk)
            # 2) entry.py 的 register 钩子
            entry = mf.get("entry", "entry.py")
            epath = pdir / entry
            if epath.is_file():
                spec = importlib.util.spec_from_file_location(f"mnemo_plugin_{name}", epath)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                if hasattr(mod, "register"):
                    mod.register(PluginContext(
                        tools=self.tools, skills=self.skills,
                        config=self.config, register_provider=register_provider,
                    ))
            self.loaded[name] = mf
            self.errors.pop(name, None)
        except Exception as e:  # noqa: BLE001
            self.errors[name] = str(e)

    def install(self, source: str, name: str | None = None) -> str:
        """source 可为 git URL 或本地路径。返回安装后的插件名。"""
        is_git = source.endswith(".git") or source.startswith(("git@", "git+")) or (
            source.startswith("http") and "github.com" in source)
        if is_git:
            url = source[4:] if source.startswith("git+") else source
            name = name or Path(url).stem
            dest = self.dir / name
            if dest.exists():
                raise FileExistsError(f"插件已存在：{name}")
            subprocess.run(["git", "clone", "--depth", "1", url, str(dest)],
                           check=True, capture_output=True, text=True)
        else:
            src = Path(source).expanduser()
            if not src.is_dir():
                raise FileNotFoundError(f"路径不存在：{src}")
            name = name or src.name
            dest = self.dir / name
            if dest.exists():
                raise FileExistsError(f"插件已存在：{name}")
            shutil.copytree(src, dest)
        if not self._manifest(dest):
            shutil.rmtree(dest, ignore_errors=True)
            raise ValueError("缺少有效的 plugin.json，安装已回滚")
        self._load_one(dest)
        return name

    def remove(self, name: str) -> bool:
        dest = self.dir / name
        if dest.is_dir():
            shutil.rmtree(dest, ignore_errors=True)
            self.loaded.pop(name, None)
            self.errors.pop(name, None)
            return True
        return False
