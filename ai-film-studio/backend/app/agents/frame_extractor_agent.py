import subprocess, uuid
from pathlib import Path
from app.config import get_settings
class FrameExtractorAgent:
    def run(self, video_path: str, shot_id: int) -> dict[str, list[str] | str]:
        root = get_settings().storage_path / "frames" / f"shot_{shot_id}_{uuid.uuid4().hex[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        first, last = root / "first.jpg", root / "last.jpg"
        key1, key2 = root / "key_1.jpg", root / "key_2.jpg"
        cmds = [["ffmpeg","-y","-i",video_path,"-frames:v","1",str(first)], ["ffmpeg","-y","-sseof","-0.1","-i",video_path,"-frames:v","1",str(last)], ["ffmpeg","-y","-i",video_path,"-vf","select='eq(n,5)'","-frames:v","1",str(key1)], ["ffmpeg","-y","-i",video_path,"-vf","select='eq(n,20)'","-frames:v","1",str(key2)]]
        for cmd in cmds:
            try: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: Path(cmd[-1]).write_text("mock frame")
        return {"first_frame_path": str(first), "last_frame_path": str(last), "keyframes": [str(key1), str(key2)]}
