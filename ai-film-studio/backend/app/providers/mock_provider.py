import hashlib, json, random, subprocess, uuid
from pathlib import Path
from typing import Any
from .base import BaseEmbeddingProvider, BaseImageProvider, BaseLLMProvider, BaseVideoProvider, BaseVisionProvider
from app.config import get_settings

class MockProvider(BaseLLMProvider, BaseImageProvider, BaseVideoProvider, BaseVisionProvider, BaseEmbeddingProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_text(self, input: dict[str, Any]) -> str:
        kind = input.get("kind", "text")
        return json.dumps({"kind": kind, "content": f"Mock AI generated {kind} for AI影视制作 Studio", "input": input}, ensure_ascii=False)

    def generate_image(self, prompt: str, references: list[str] | None = None) -> str:
        path = self.settings.storage_path / "props" / f"mock_{uuid.uuid4().hex}.svg"
        path.write_text(f"<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360'><rect width='100%' height='100%' fill='#222'/><text x='40' y='180' fill='white'>{prompt[:40]}</text></svg>")
        return str(path)

    def generate_video(self, prompt: str, first_frame: str | None, references: list[str], duration: int, aspect_ratio: str) -> str:
        output = self.settings.storage_path / "videos" / f"shot_{uuid.uuid4().hex}.mp4"
        color = hashlib.md5(prompt.encode()).hexdigest()[:6]
        size = "1280x720" if aspect_ratio != "9:16" else "720x1280"
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=#{color}:s={size}:d={duration}", "-vf", f"drawtext=text='AI Film Shot':fontcolor=white:fontsize=48:x=40:y=60", "-pix_fmt", "yuv420p", str(output)]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            output.write_bytes(b"mock video placeholder")
        return str(output)

    def analyze_frames(self, frames: list[str]) -> dict[str, Any]:
        return {
            "characters": ["char_hero", "char_heroine"],
            "animals": ["guardian_beast"],
            "buildings": ["main_location_gate"],
            "backgrounds": ["primary_scene"],
            "props": ["prop_key_01", "prop_token_02"],
            "costumes": {"char_hero": "深色长外套，银色肩章", "char_heroine": "浅色作战服，蓝色围巾"},
            "weather": "微风，无雨", "time": "黄昏", "color_palette": "青金色电影感", "camera_direction": "由左向右推进",
            "conflicts": [], "continuity_notes": "保持角色脸型、发型、服装、建筑入口、青金色调与上一镜头一致。"
        }

    def embed_text(self, text: str) -> list[float]:
        rnd = random.Random(hashlib.sha256(text.encode()).hexdigest())
        return [rnd.uniform(-1, 1) for _ in range(1536)]

    def embed_image(self, image_path: str) -> list[float]:
        return self.embed_text(image_path)
