import subprocess, uuid
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, selectinload
from app.agents.art_director_agent import ArtDirectorAgent
from app.agents.casting_agent import CastingAgent
from app.agents.continuity_agent import ContinuityAgent
from app.agents.director_agent import DirectorAgent
from app.agents.frame_extractor_agent import FrameExtractorAgent
from app.agents.memory_anchor_agent import MemoryAnchorAgent
from app.agents.prompt_director_agent import PromptDirectorAgent
from app.agents.repair_agent import RepairAgent
from app.agents.storyboard_agent import StoryboardAgent
from app.agents.video_generation_agent import VideoGenerationAgent
from app.agents.vision_supervisor_agent import VisionSupervisorAgent
from app.agents.writer_agent import WriterAgent
from app.config import get_settings
from app.models.studio import Asset, Character, ContinuityReport, Export, GenerationTask, MemoryAnchor, Project, Script, Shot, ShotPrompt, StoryBible
from app.schemas.studio import ProjectCreate

class StudioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump(), status="draft")
        self.db.add(project); self.db.commit(); self.db.refresh(project); return project

    def list_projects(self) -> list[Project]:
        return list(self.db.scalars(select(Project).order_by(Project.created_at.desc())))

    def get_project(self, project_id: int) -> Project:
        stmt = select(Project).where(Project.id == project_id).options(selectinload(Project.story_bible), selectinload(Project.script), selectinload(Project.characters), selectinload(Project.assets), selectinload(Project.shots))
        project = self.db.scalar(stmt)
        if not project: raise ValueError("Project not found")
        return project

    def generate_story_bible(self, project_id: int) -> StoryBible:
        project = self.get_project(project_id)
        self.db.execute(delete(StoryBible).where(StoryBible.project_id == project_id))
        bible = StoryBible(project_id=project_id, **DirectorAgent().run(project))
        project.status = "story_bible_ready"
        self.db.add(bible); self.db.commit(); self.db.refresh(bible); return bible

    def generate_script(self, project_id: int) -> Script:
        project = self.get_project(project_id); bible = project.story_bible or self.generate_story_bible(project_id)
        self.db.execute(delete(Script).where(Script.project_id == project_id))
        script = Script(project_id=project_id, **WriterAgent().run(bible))
        project.status = "script_ready"
        self.db.add(script); self.db.commit(); self.db.refresh(script); return script

    def generate_characters(self, project_id: int) -> list[Character]:
        self.get_project(project_id); self.db.execute(delete(Character).where(Character.project_id == project_id))
        chars = []
        for item in CastingAgent().run():
            c = Character(project_id=project_id, is_selected=False, is_locked=False, reference_front_path="/storage/characters/mock_front.svg", reference_side_path="/storage/characters/mock_side.svg", reference_full_body_path="/storage/characters/mock_full.svg", expression_sheet_path="/storage/characters/mock_expr.svg", **item)
            self.db.add(c); chars.append(c)
        self.get_project(project_id).status = "casting_ready"
        self.db.commit(); [self.db.refresh(c) for c in chars]; return chars

    def select_character(self, project_id: int, character_id: int) -> Character:
        char = self.db.get(Character, character_id)
        if not char or char.project_id != project_id: raise ValueError("Character not found")
        for other in self.db.scalars(select(Character).where(Character.project_id == project_id, Character.role_type == char.role_type)):
            other.is_selected = other.id == character_id; other.is_locked = other.id == character_id
        self.get_project(project_id).status = "characters_locked"
        self.db.commit(); self.db.refresh(char); return char

    def auto_select_characters(self, project_id: int) -> list[Character]:
        chars = list(self.db.scalars(select(Character).where(Character.project_id == project_id))) or self.generate_characters(project_id)
        selected = []
        for role in sorted({c.role_type for c in chars}):
            role_chars = [c for c in chars if c.role_type == role]
            best = max(role_chars, key=lambda c: c.score)
            for c in role_chars: c.is_selected, c.is_locked = (c.id == best.id), (c.id == best.id)
            selected.append(best)
        self.get_project(project_id).status = "characters_locked"
        self.db.commit(); return selected

    def generate_assets(self, project_id: int) -> list[Asset]:
        self.get_project(project_id); self.db.execute(delete(Asset).where(Asset.project_id == project_id))
        assets=[]
        for item in ArtDirectorAgent().run():
            a=Asset(project_id=project_id, reference_image_path="/storage/props/mock_asset.svg", is_locked=False, **item); self.db.add(a); assets.append(a)
        self.get_project(project_id).status="assets_ready"; self.db.commit(); [self.db.refresh(a) for a in assets]; return assets

    def generate_shots(self, project_id: int) -> list[Shot]:
        self.get_project(project_id); self.db.execute(delete(Shot).where(Shot.project_id == project_id))
        shots=[]
        for item in StoryboardAgent().run():
            s=Shot(project_id=project_id, status="pending", **item); self.db.add(s); shots.append(s)
        self.get_project(project_id).status="shots_ready"; self.db.commit(); [self.db.refresh(s) for s in shots]; return shots

    def _memory_context(self, project_id: int) -> str:
        anchors = list(self.db.scalars(select(MemoryAnchor).where(MemoryAnchor.project_id==project_id).order_by(MemoryAnchor.created_at.desc()).limit(3)))
        return "\n".join([f"Shot {a.shot_id}: {a.continuity_notes}; {a.style_lock}; 下一镜头继承尾帧 {a.last_frame_path}" for a in anchors])

    def generate_prompt(self, shot_id: int) -> ShotPrompt:
        shot = self.db.get(Shot, shot_id)
        if not shot: raise ValueError("Shot not found")
        project = self.get_project(shot.project_id)
        prev = self.db.scalar(select(Shot).where(Shot.project_id==shot.project_id, Shot.shot_number==shot.shot_number-1))
        first_frame = prev.last_frame_path if prev and prev.last_frame_path else shot.first_frame_path
        shot.first_frame_path = first_frame
        memory_context = self._memory_context(project.id)
        data = PromptDirectorAgent().run(project, shot, project.characters, project.assets, memory_context, first_frame)
        prompt = ShotPrompt(shot_id=shot.id, memory_context=memory_context, first_frame_path=first_frame, **data)
        shot.status = "prompt_ready"; self.db.add(prompt); self.db.commit(); self.db.refresh(prompt); return prompt

    def generate_video(self, shot_id: int) -> GenerationTask:
        shot = self.db.get(Shot, shot_id)
        if not shot: raise ValueError("Shot not found")
        prompt = self.db.scalar(select(ShotPrompt).where(ShotPrompt.shot_id==shot_id).order_by(ShotPrompt.created_at.desc())) or self.generate_prompt(shot_id)
        task = GenerationTask(project_id=shot.project_id, shot_id=shot.id, provider_name="mock", status="running", request_payload={"prompt": prompt.prompt_text}, response_payload={}, retry_count=0)
        self.db.add(task); shot.status="generating"; self.db.commit()
        try:
            path = VideoGenerationAgent().run(prompt.prompt_text, prompt.first_frame_path, shot.duration_seconds, self.get_project(shot.project_id).aspect_ratio)
            task.status="success"; task.output_video_path=path; task.response_payload={"video_path": path}; shot.video_path=path; shot.status="generated"
        except Exception as exc:
            task.status="failed"; task.error_message=str(exc); shot.status="failed"
        self.db.commit(); self.db.refresh(task); return task

    def extract_frames(self, shot_id: int) -> Shot:
        shot = self.db.get(Shot, shot_id)
        if not shot or not shot.video_path: raise ValueError("Generated shot video required")
        shot.status="extracting_frames"; self.db.commit()
        data = FrameExtractorAgent().run(shot.video_path, shot.id)
        shot.first_frame_path = str(data["first_frame_path"]); shot.last_frame_path = str(data["last_frame_path"])
        setattr(shot, "_keyframes", data["keyframes"])
        shot.status="generated"; self.db.commit(); self.db.refresh(shot); return shot

    def create_memory_anchor(self, shot_id: int) -> MemoryAnchor:
        shot = self.db.get(Shot, shot_id)
        if not shot: raise ValueError("Shot not found")
        keyframes = []
        frame_dir = Path(shot.first_frame_path or "").parent
        if frame_dir.exists(): keyframes = [str(p) for p in frame_dir.glob("key_*.jpg")]
        frames = [p for p in [shot.first_frame_path, shot.last_frame_path, *keyframes] if p]
        analysis = VisionSupervisorAgent().run(frames)
        data = MemoryAnchorAgent().run(analysis, shot.first_frame_path, shot.last_frame_path, keyframes)
        anchor = MemoryAnchor(project_id=shot.project_id, shot_id=shot.id, **data)
        shot.status="memory_created"; self.db.add(anchor); self.db.commit(); self.db.refresh(anchor); return anchor

    def review_continuity(self, shot_id: int) -> ContinuityReport:
        shot = self.db.get(Shot, shot_id)
        if not shot: raise ValueError("Shot not found")
        retry = self.db.scalar(select(GenerationTask.retry_count).where(GenerationTask.shot_id==shot_id).order_by(GenerationTask.created_at.desc())) or 0
        data = ContinuityAgent().run(shot.shot_number, retry, self.settings.continuity_pass_score)
        report = ContinuityReport(project_id=shot.project_id, shot_id=shot.id, **data)
        shot.status = "passed" if data["passed"] else "failed"
        self.db.add(report); self.db.commit(); self.db.refresh(report); return report

    def repair_and_retry(self, shot_id: int) -> ContinuityReport:
        shot = self.db.get(Shot, shot_id)
        if not shot: raise ValueError("Shot not found")
        task = self.db.scalar(select(GenerationTask).where(GenerationTask.shot_id==shot_id).order_by(GenerationTask.created_at.desc()))
        retries = (task.retry_count if task else 0) + 1
        if retries > self.settings.max_shot_retry:
            shot.status="needs_manual_fix"; self.db.commit(); raise ValueError("Max retries exceeded")
        report = self.db.scalar(select(ContinuityReport).where(ContinuityReport.shot_id==shot_id).order_by(ContinuityReport.created_at.desc()))
        prompt = self.db.scalar(select(ShotPrompt).where(ShotPrompt.shot_id==shot_id).order_by(ShotPrompt.created_at.desc())) or self.generate_prompt(shot_id)
        fixed = RepairAgent().run(prompt.prompt_text, report.failure_reasons if report else "", report.repair_suggestions if report else "")
        self.db.add(ShotPrompt(shot_id=shot.id, prompt_text=fixed, negative_prompt=prompt.negative_prompt, memory_context=prompt.memory_context, first_frame_path=prompt.first_frame_path))
        shot.status="retrying"; self.db.commit()
        new_task = self.generate_video(shot_id); new_task.retry_count = retries; self.db.commit()
        self.extract_frames(shot_id); self.create_memory_anchor(shot_id); return self.review_continuity(shot_id)

    def generate_all(self, project_id: int) -> Export:
        project = self.get_project(project_id); project.status="generating"; self.db.commit()
        self.generate_story_bible(project_id); self.generate_script(project_id); self.generate_characters(project_id); self.auto_select_characters(project_id); self.generate_assets(project_id); shots = self.generate_shots(project_id)
        for shot in shots:
            self.generate_prompt(shot.id); self.generate_video(shot.id); self.extract_frames(shot.id); self.create_memory_anchor(shot.id); report = self.review_continuity(shot.id)
            while not report.passed:
                report = self.repair_and_retry(shot.id)
        project.status="reviewing"; self.db.commit(); return self.export_project(project_id)

    def export_project(self, project_id: int) -> Export:
        project = self.get_project(project_id)
        output = self.settings.storage_path / "exports" / f"project_{project_id}_{uuid.uuid4().hex[:8]}.mp4"
        list_file = self.settings.storage_path / "exports" / f"concat_{project_id}.txt"
        videos = [s.video_path for s in project.shots if s.video_path and s.status == "passed"]
        list_file.write_text("\n".join([f"file '{v}'" for v in videos]))
        try:
            subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(list_file),"-c","copy",str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            output.write_text("mock export")
        exp = Export(project_id=project_id, final_video_path=str(output), subtitle_path=None, audio_path=None, status="completed")
        project.status="completed"; self.db.add(exp); self.db.commit(); self.db.refresh(exp); return exp

    def memory_anchors(self, project_id:int) -> list[MemoryAnchor]:
        return list(self.db.scalars(select(MemoryAnchor).where(MemoryAnchor.project_id==project_id).order_by(MemoryAnchor.created_at)))
    def continuity_reports(self, project_id:int) -> list[ContinuityReport]:
        return list(self.db.scalars(select(ContinuityReport).where(ContinuityReport.project_id==project_id).order_by(ContinuityReport.created_at)))
