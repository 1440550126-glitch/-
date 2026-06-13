from app.providers.factory import get_video_provider
class VideoGenerationAgent:
    def run(self, prompt: str, first_frame: str | None, duration: int, aspect_ratio: str) -> str:
        return get_video_provider().generate_video(prompt, first_frame, [], duration, aspect_ratio)
