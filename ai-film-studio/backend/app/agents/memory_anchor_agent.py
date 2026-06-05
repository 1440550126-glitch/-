from app.providers.factory import get_embedding_provider
class MemoryAnchorAgent:
    def run(self, analysis: dict, first_frame: str | None, last_frame: str | None, keyframes: list[str]) -> dict:
        continuity = analysis.get("continuity_notes", "保持连续性")
        style_lock = f"色调:{analysis.get('color_palette')}; 时间:{analysis.get('time')}; 天气:{analysis.get('weather')}; 镜头方向:{analysis.get('camera_direction')}"
        return {"memory_type": "shot_visual_supervision", "entities_json": analysis, "scene_description": f"{analysis.get('backgrounds')} / {analysis.get('buildings')}", "continuity_notes": continuity, "style_lock": style_lock, "first_frame_path": first_frame, "last_frame_path": last_frame, "keyframes_json": keyframes, "embedding_vector": get_embedding_provider().embed_text(continuity + style_lock)}
