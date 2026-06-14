"""持续感知：盯着摄像头，认出"谁在画面里"，有人进入/离开时触发回调。

核心状态机 observe() 是纯逻辑、可单测的：负责"新进入"判定和"离开"去抖
（短暂消失不算离开，超过 forget_after 才算）。run() 才需要 opencv。
"""

from __future__ import annotations

import time


class PresenceMonitor:
    def __init__(
        self,
        perception,
        on_enter=None,
        on_leave=None,
        camera_index: int = 0,
        forget_after: float = 5.0,
    ) -> None:
        self.perception = perception
        self.on_enter = on_enter or (lambda name: None)
        self.on_leave = on_leave or (lambda name: None)
        self.camera_index = camera_index
        self.forget_after = forget_after
        self.present: dict[str, float] = {}  # name -> 最后一次看到的时间
        self._cv2 = None
        try:
            import cv2

            self._cv2 = cv2
        except Exception:
            self._cv2 = None

    @property
    def available(self) -> bool:
        return self._cv2 is not None and getattr(self.perception, "available", False)

    def observe(self, names_now, now: float | None = None) -> tuple[list, list]:
        """传入"当前画面里识别到的人名集合"，返回 (刚进入的, 刚离开的)。"""
        now = time.time() if now is None else now
        names_now = set(names_now)
        entered, left = [], []

        for n in names_now:
            if n not in self.present:
                entered.append(n)
                self.on_enter(n)
            self.present[n] = now  # 刷新"最后看到"

        for n in list(self.present):
            if n not in names_now and now - self.present[n] > self.forget_after:
                left.append(n)
                self.on_leave(n)
                del self.present[n]

        return entered, left

    def run(self, poll_interval: float = 1.0) -> None:
        """阻塞式摄像头循环。需要 opencv 与可用的人脸识别。"""
        if self._cv2 is None:
            raise RuntimeError("需要 opencv-python 才能开摄像头：pip install opencv-python")
        cap = self._cv2.VideoCapture(self.camera_index)
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                rgb = frame[:, :, ::-1]  # BGR -> RGB
                self.observe(set(self.perception.identify_frame(rgb)))
                time.sleep(poll_interval)
        finally:
            cap.release()
