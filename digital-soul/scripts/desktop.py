#!/usr/bin/env python3
"""数字分身 · 桌面聊天界面（Tkinter —— Python 自带，无需额外安装）。

Linux 若提示缺 tkinter：sudo apt install python3-tk
用法：python scripts/desktop.py
"""

import pathlib
import queue
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    import tkinter as tk
    from tkinter import scrolledtext, ttk
except Exception:
    sys.exit("未找到 tkinter。Linux 请先安装：sudo apt install python3-tk")

from dsoul.annotate import EMOJI  # noqa: E402
from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402


class App:
    def __init__(self, root: "tk.Tk") -> None:
        self.root = root
        self.agent = build_agent()
        self.name = self.agent.identity.get("name", "我")
        self.q: queue.Queue = queue.Queue()

        root.title(f"{self.name} · 数字分身")
        root.geometry("700x580")
        self._build()
        self._poll()
        self._system(self._status())

    # ---------- 界面 ----------
    def _build(self) -> None:
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="说话人：").pack(side="left")
        people = [p["name"] for p in self.agent.authority.people.values()]
        self.speaker = tk.StringVar(value=self._owner())
        ttk.Combobox(top, textvariable=self.speaker, values=people, width=12).pack(side="left", padx=4)
        ttk.Button(top, text="时间线", command=self._timeline).pack(side="right", padx=2)
        ttk.Button(top, text="睡一觉", command=self._sleep).pack(side="right", padx=2)
        ttk.Button(top, text="清屏", command=self._clear).pack(side="right", padx=2)

        self.log = scrolledtext.ScrolledText(self.root, wrap="word", state="disabled", font=("", 11))
        self.log.pack(fill="both", expand=True, padx=6, pady=4)
        self.log.tag_config("me", foreground="#1565c0")
        self.log.tag_config("soul", foreground="#2e7d32")
        self.log.tag_config("sys", foreground="#999999")

        bottom = ttk.Frame(self.root, padding=6)
        bottom.pack(fill="x")
        self.entry = ttk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()
        ttk.Button(bottom, text="发送", command=self._send).pack(side="left", padx=4)
        self.status = ttk.Label(self.root, text="", foreground="#999999", padding=(8, 0))
        self.status.pack(fill="x")

    def _owner(self) -> str:
        for p in self.agent.authority.people.values():
            if p.get("trust") == "owner":
                return p["name"]
        return self.name

    def _status(self) -> str:
        a = self.agent
        llm = "本地大模型 ✅" if a.llm.available else "降级模式（未接大模型）"
        return f"{llm} ｜ 记忆 {len(a.memory.items)} 条 ｜ 检索 {a.memory.embedder.mode}"

    # ---------- 输出 ----------
    def _append(self, who: str, text: str, tag: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{who}: ", (tag,))
        self.log.insert("end", text + "\n", (tag,))
        self.log.configure(state="disabled")
        self.log.see("end")

    def _system(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"— {text} —\n", ("sys",))
        self.log.configure(state="disabled")
        self.log.see("end")

    # ---------- 交互 ----------
    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        speaker = self.speaker.get().strip() or self._owner()
        self._append(speaker, text, "me")
        self.status.config(text="思考中…")
        threading.Thread(target=self._worker, args=(speaker, text), daemon=True).start()

    def _worker(self, speaker: str, text: str) -> None:
        try:
            res = self.agent.handle(speaker, text)
            self.q.put(res["reply"])
        except Exception as e:
            self.q.put(f"（出错了：{e}）")

    def _poll(self) -> None:
        try:
            while True:
                reply = self.q.get_nowait()
                self.status.config(text="")
                self._append(self.name, reply, "soul")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _timeline(self) -> None:
        self._system("情感时间线")
        cur = None
        for it in self.agent.memory.timeline():
            when = it.get("when") or "时间未知"
            if when != cur:
                self._system(f"【{when}】")
                cur = when
            self._append(EMOJI.get(it.get("emotion", "平静"), "·"), it["text"], "sys")

    def _sleep(self) -> None:
        rep = Consolidator(
            self.agent.memory, self.agent.journal, llm=self.agent.llm,
            identity=self.agent.identity, authority=self.agent.authority,
        ).run()
        self._system(f"😴 巩固 {rep['processed']} 条对话，新增 {len(rep['learned'])} 条长期记忆")
        for m in rep["learned"]:
            self._append("+", m, "sys")

    def _clear(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._system(self._status())


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
