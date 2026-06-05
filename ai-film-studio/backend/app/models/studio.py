from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(50))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)
    aspect_ratio: Mapped[str] = mapped_column(String(20))
    visual_style: Mapped[str] = mapped_column(String(80))
    director_personality: Mapped[str] = mapped_column(String(80))
    target_audience: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    story_bible = relationship("StoryBible", back_populates="project", uselist=False, cascade="all, delete-orphan")
    script = relationship("Script", back_populates="project", uselist=False, cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    shots = relationship("Shot", back_populates="project", cascade="all, delete-orphan", order_by="Shot.shot_number")

class StoryBible(Base, TimestampMixin):
    __tablename__ = "story_bibles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    world_view: Mapped[str] = mapped_column(Text)
    core_hook: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(Text)
    emotion_curve: Mapped[str] = mapped_column(Text)
    director_notes: Mapped[str] = mapped_column(Text)
    visual_rules: Mapped[str] = mapped_column(Text)
    negative_rules: Mapped[str] = mapped_column(Text)
    project = relationship("Project", back_populates="story_bible")

class Script(Base, TimestampMixin):
    __tablename__ = "scripts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    synopsis: Mapped[str] = mapped_column(Text)
    three_act_structure: Mapped[dict] = mapped_column(JSON)
    scene_script: Mapped[dict] = mapped_column(JSON)
    dialogue: Mapped[dict] = mapped_column(JSON)
    shot_outline: Mapped[dict] = mapped_column(JSON)
    project = relationship("Project", back_populates="script")

class Character(Base, TimestampMixin):
    __tablename__ = "characters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    role_type: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    personality: Mapped[str] = mapped_column(Text)
    appearance: Mapped[str] = mapped_column(Text)
    costume: Mapped[str] = mapped_column(Text)
    voice_profile: Mapped[str] = mapped_column(Text)
    reference_front_path: Mapped[str | None] = mapped_column(String(500))
    reference_side_path: Mapped[str | None] = mapped_column(String(500))
    reference_full_body_path: Mapped[str | None] = mapped_column(String(500))
    expression_sheet_path: Mapped[str | None] = mapped_column(String(500))
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0)
    project = relationship("Project", back_populates="characters")

class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_type: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    reference_image_path: Mapped[str | None] = mapped_column(String(500))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    project = relationship("Project", back_populates="assets")

class Shot(Base, TimestampMixin):
    __tablename__ = "shots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    shot_number: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    story_goal: Mapped[str] = mapped_column(Text)
    characters_json: Mapped[list] = mapped_column(JSON)
    location_id: Mapped[int | None] = mapped_column(Integer)
    props_json: Mapped[list] = mapped_column(JSON)
    camera_instruction: Mapped[str] = mapped_column(Text)
    action_instruction: Mapped[str] = mapped_column(Text)
    lighting_instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    video_path: Mapped[str | None] = mapped_column(String(500))
    first_frame_path: Mapped[str | None] = mapped_column(String(500))
    last_frame_path: Mapped[str | None] = mapped_column(String(500))
    project = relationship("Project", back_populates="shots")
    prompts = relationship("ShotPrompt", back_populates="shot", cascade="all, delete-orphan")

class ShotPrompt(Base, TimestampMixin):
    __tablename__ = "shot_prompts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    prompt_text: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text)
    memory_context: Mapped[str] = mapped_column(Text, default="")
    first_frame_path: Mapped[str | None] = mapped_column(String(500))
    shot = relationship("Shot", back_populates="prompts")

class GenerationTask(Base, TimestampMixin):
    __tablename__ = "generation_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    provider_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    output_video_path: Mapped[str | None] = mapped_column(String(500))

class MemoryAnchor(Base, TimestampMixin):
    __tablename__ = "memory_anchors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    memory_type: Mapped[str] = mapped_column(String(80), default="shot_visual_supervision")
    entities_json: Mapped[dict] = mapped_column(JSON)
    scene_description: Mapped[str] = mapped_column(Text)
    continuity_notes: Mapped[str] = mapped_column(Text)
    style_lock: Mapped[str] = mapped_column(Text)
    first_frame_path: Mapped[str | None] = mapped_column(String(500))
    last_frame_path: Mapped[str | None] = mapped_column(String(500))
    keyframes_json: Mapped[list] = mapped_column(JSON)
    embedding_vector: Mapped[list[float]] = mapped_column(Vector(1536))

class ContinuityReport(Base):
    __tablename__ = "continuity_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    character_score: Mapped[float] = mapped_column(Float)
    background_score: Mapped[float] = mapped_column(Float)
    costume_score: Mapped[float] = mapped_column(Float)
    prop_score: Mapped[float] = mapped_column(Float)
    color_score: Mapped[float] = mapped_column(Float)
    transition_score: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    failure_reasons: Mapped[str] = mapped_column(Text)
    repair_suggestions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Export(Base, TimestampMixin):
    __tablename__ = "exports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    final_video_path: Mapped[str | None] = mapped_column(String(500))
    subtitle_path: Mapped[str | None] = mapped_column(String(500))
    audio_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="pending")
