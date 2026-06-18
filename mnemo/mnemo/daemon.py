"""7×24 守护进程：持久化任务 + 调度器。让 Mnemo 在后台自动跑任务。

调度语法（schedule）：
  every 30s / 5m / 2h / 1d   固定间隔
  @hourly                    每小时
  @daily 09:00               每天定点（缺省 09:00）
  @startup                   守护进程启动时跑一次
"""
from __future__ import annotations

import re
import signal
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_UNIT = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_schedule(spec: str):
    s = (spec or "").strip().lower()
    if s in ("@startup", "startup"):
        return ("startup", None)
    if s == "@hourly":
        return ("interval", 3600)
    if s.startswith("@daily"):
        suffix = s[len("@daily"):].strip()
        if not suffix:
            return ("daily", (9, 0))
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", suffix)
        if not m:
            raise ValueError(f"无法解析调度语法：{spec}")
        hh, mm = int(m.group(1)), int(m.group(2))
        if hh > 23 or mm > 59:
            raise ValueError(f"非法时间（HH:MM 越界）：{spec}")
        return ("daily", (hh, mm))
    m = re.match(r"(?:every\s+)?(\d+)\s*([smhd])$", s)
    if m:
        return ("interval", int(m.group(1)) * _UNIT[m.group(2)])
    if s.isdigit():
        return ("interval", int(s))
    raise ValueError(f"无法解析调度语法：{spec}")


def compute_next(spec: str, from_ts: float) -> float | None:
    kind, val = parse_schedule(spec)
    if kind == "interval":
        return from_ts + val
    if kind == "daily":
        hh, mm = val
        dt = datetime.fromtimestamp(from_ts).replace(
            hour=hh, minute=mm, second=0, microsecond=0)
        if dt.timestamp() <= from_ts:
            dt += timedelta(days=1)
        return dt.timestamp()
    return None  # startup：不参与定时


@dataclass
class Task:
    id: int
    name: str
    prompt: str
    schedule: str
    enabled: int
    last_run: float | None
    next_run: float | None
    last_result: str | None


class TaskStore:
    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, prompt TEXT, schedule TEXT,
                enabled INTEGER DEFAULT 1,
                created_at REAL, last_run REAL, next_run REAL, last_result TEXT
            );
            CREATE TABLE IF NOT EXISTS runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER, started_at REAL, ok INTEGER, output TEXT
            );
            """
        )
        self.db.commit()

    def add(self, name: str, prompt: str, schedule: str, enabled: bool = True) -> int:
        parse_schedule(schedule)  # 提前校验
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO tasks(name,prompt,schedule,enabled,created_at,next_run)"
            " VALUES(?,?,?,?,?,?)",
            (name, prompt, schedule, int(enabled), now, compute_next(schedule, now)),
        )
        self.db.commit()
        return cur.lastrowid

    def _row(self, r) -> Task:
        return Task(r["id"], r["name"], r["prompt"], r["schedule"], r["enabled"],
                    r["last_run"], r["next_run"], r["last_result"])

    def list(self) -> list[Task]:
        return [self._row(r) for r in
                self.db.execute("SELECT * FROM tasks ORDER BY id").fetchall()]

    def get(self, tid: int) -> Task | None:
        r = self.db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        return self._row(r) if r else None

    def remove(self, tid: int) -> bool:
        cur = self.db.execute("DELETE FROM tasks WHERE id=?", (tid,))
        self.db.commit()
        return cur.rowcount > 0

    def set_enabled(self, tid: int, enabled: bool) -> None:
        self.db.execute("UPDATE tasks SET enabled=? WHERE id=?", (int(enabled), tid))
        self.db.commit()

    def due(self, now: float) -> list[Task]:
        rows = self.db.execute(
            "SELECT * FROM tasks WHERE enabled=1 AND next_run IS NOT NULL AND next_run<=?",
            (now,),
        ).fetchall()
        return [self._row(r) for r in rows]

    def startup_tasks(self) -> list[Task]:
        return [t for t in self.list()
                if t.enabled and parse_schedule(t.schedule)[0] == "startup"]

    def mark_run(self, task: Task, ok: bool, output: str) -> None:
        now = time.time()
        nxt = compute_next(task.schedule, now)
        self.db.execute(
            "UPDATE tasks SET last_run=?, next_run=?, last_result=? WHERE id=?",
            (now, nxt, output[:2000], task.id),
        )
        self.db.execute(
            "INSERT INTO runs(task_id,started_at,ok,output) VALUES(?,?,?,?)",
            (task.id, now, int(ok), output[:8000]),
        )
        self.db.commit()


class Scheduler:
    def __init__(self, agent, store: TaskStore, log=print):
        self.agent = agent
        self.store = store
        self.log = log
        self._stop = False

    def _run_task(self, task: Task) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log(f"[{ts}] ▶ 运行任务 #{task.id} {task.name}")
        try:
            out = self.agent.run(task.prompt, session=f"daemon:{task.name}", auto_approve=True)
            self.store.mark_run(task, True, out)
            self.log(f"[{ts}] ✓ 完成 #{task.id}: {out[:160].strip()}")
        except Exception as e:  # noqa: BLE001
            self.store.mark_run(task, False, f"ERROR: {e}")
            self.log(f"[{ts}] ✗ 任务 #{task.id} 失败：{e}")

    def _maintenance(self, now: float) -> None:
        """主动式记忆：到点提醒 + 每日记忆巩固。"""
        mem = getattr(self.agent, "memory", None)
        if not mem:
            return
        for rem in mem.due_reminders(now):
            ts = datetime.now().strftime("%H:%M")
            self.log(f"[{ts}] 🔔 提醒：{rem['text']}")
            mem.mark_reminder_done(rem["id"])
        last = float(mem.get_profile("last_consolidate", "0") or 0)
        if now - last > 86400:
            res = mem.consolidate()
            mem.set_profile("last_consolidate", str(int(now)))
            if res["merged"] or res["forgotten"]:
                self.log(f"🧠 记忆巩固：合并 {res['merged']}，淡忘 {res['forgotten']}，"
                         f"保留 {res['kept']}")

    def run_once(self, now: float | None = None) -> int:
        now = now or time.time()
        self._maintenance(now)
        due = self.store.due(now)
        for t in due:
            self._run_task(t)
        return len(due)

    def serve(self, interval: int = 30) -> None:
        pid_file = Path(self.store.db.execute("PRAGMA database_list").fetchone()[2]).parent / "daemon.pid"
        pid_file.write_text(str(__import__("os").getpid()))

        def _sig(*_):
            self._stop = True
        signal.signal(signal.SIGINT, _sig)
        signal.signal(signal.SIGTERM, _sig)

        self.log(f"Mnemo 守护进程启动（每 {interval}s 巡检一次，Ctrl-C 退出）")
        for t in self.store.startup_tasks():
            self._run_task(t)
        try:
            while not self._stop:
                self.run_once()
                slept = 0
                while slept < interval and not self._stop:
                    time.sleep(1)
                    slept += 1
        finally:
            pid_file.unlink(missing_ok=True)
            self.log("守护进程已停止")
