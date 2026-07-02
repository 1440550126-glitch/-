"""对话日记：把每次互动追加记录下来，作为"短期记忆"，等待巩固成长期记忆。

journal.jsonl 追加写入；journal.state.json 记一个 cursor 标记"已巩固到第几条"，
保证巩固幂等、不会重复学习。属于隐私数据，默认 gitignore。
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class Journal:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.state_path = self.path.with_name(self.path.stem + ".state.json")
        self.cursor = 0
        if self.state_path.exists():
            try:
                self.cursor = json.loads(
                    self.state_path.read_text(encoding="utf-8")
                ).get("cursor", 0)
            except Exception:
                self.cursor = 0

    def append(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.time(), **entry}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for ln in self.path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return out

    def unconsolidated(self) -> list[dict]:
        return self._all()[self.cursor:]

    def mark_consolidated(self) -> None:
        self.cursor = len(self._all())
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps({"cursor": self.cursor}), encoding="utf-8"
        )

    def __len__(self) -> int:
        return len(self._all())
