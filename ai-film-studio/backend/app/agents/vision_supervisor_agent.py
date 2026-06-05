from app.providers.factory import get_vision_provider
class VisionSupervisorAgent:
    def run(self, frames: list[str]) -> dict:
        return get_vision_provider().analyze_frames(frames)
