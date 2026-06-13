from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    title: str
    type: str
    duration_seconds: int = 60
    aspect_ratio: str
    visual_style: str
    director_personality: str
    target_audience: str = ""
class SelectCharacterRequest(BaseModel):
    character_id: int
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class StoryBibleOut(ORMModel):
    id:int; project_id:int; world_view:str; core_hook:str; tone:str; emotion_curve:str; director_notes:str; visual_rules:str; negative_rules:str
class ScriptOut(ORMModel):
    id:int; project_id:int; synopsis:str; three_act_structure:dict[str,Any]; scene_script:dict[str,Any]; dialogue:dict[str,Any]; shot_outline:dict[str,Any]
class CharacterOut(ORMModel):
    id:int; project_id:int; role_type:str; name:str; personality:str; appearance:str; costume:str; voice_profile:str; reference_front_path:str|None; reference_side_path:str|None; reference_full_body_path:str|None; expression_sheet_path:str|None; is_selected:bool; is_locked:bool; score:float
class AssetOut(ORMModel):
    id:int; project_id:int; asset_type:str; name:str; description:str; reference_image_path:str|None; is_locked:bool
class ShotPromptOut(ORMModel):
    id:int; shot_id:int; prompt_text:str; negative_prompt:str; memory_context:str; first_frame_path:str|None
class ShotOut(ORMModel):
    id:int; project_id:int; shot_number:int; duration_seconds:int; story_goal:str; characters_json:list[Any]; location_id:int|None; props_json:list[Any]; camera_instruction:str; action_instruction:str; lighting_instruction:str; status:str; video_path:str|None; first_frame_path:str|None; last_frame_path:str|None
class MemoryAnchorOut(ORMModel):
    id:int; project_id:int; shot_id:int; memory_type:str; entities_json:dict[str,Any]; scene_description:str; continuity_notes:str; style_lock:str; first_frame_path:str|None; last_frame_path:str|None; keyframes_json:list[Any]; created_at:datetime
class ContinuityReportOut(ORMModel):
    id:int; project_id:int; shot_id:int; character_score:float; background_score:float; costume_score:float; prop_score:float; color_score:float; transition_score:float; total_score:float; passed:bool; failure_reasons:str; repair_suggestions:str; created_at:datetime
class ExportOut(ORMModel):
    id:int; project_id:int; final_video_path:str|None; subtitle_path:str|None; audio_path:str|None; status:str
class ProjectOut(ORMModel):
    id:int; title:str; type:str; duration_seconds:int; aspect_ratio:str; visual_style:str; director_personality:str; target_audience:str; status:str; created_at:datetime; updated_at:datetime
    story_bible: StoryBibleOut | None = None
    script: ScriptOut | None = None
    characters: list[CharacterOut] = []
    assets: list[AssetOut] = []
    shots: list[ShotOut] = []
