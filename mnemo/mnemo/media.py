"""多模态媒体辅助：用 ffmpeg（若可用）从视频里抽取关键帧供视觉模型理解。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXT


def extract_frames(video_path: str, n: int = 3, out_dir: str | None = None) -> list[str]:
    """均匀抽取 n 帧，返回图片路径列表；无 ffmpeg 或失败则返回 []。"""
    if not shutil.which("ffmpeg") or not Path(video_path).is_file():
        return []
    out_dir = out_dir or tempfile.mkdtemp(prefix="mnemo_frames_")
    # fps 过滤难以精确取 n 帧，这里用 thumbnail+select 简化：每隔若干帧取一张
    pattern = str(Path(out_dir) / "frame_%03d.jpg")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vf",
             f"thumbnail,fps=1/2", "-frames:v", str(n), pattern],
            capture_output=True, timeout=120)
    except Exception:  # noqa: BLE001
        return []
    return sorted(str(p) for p in Path(out_dir).glob("frame_*.jpg"))
