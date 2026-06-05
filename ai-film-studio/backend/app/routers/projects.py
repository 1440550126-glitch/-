from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.studio import AssetOut, CharacterOut, ContinuityReportOut, ExportOut, MemoryAnchorOut, ProjectCreate, ProjectOut, ScriptOut, SelectCharacterRequest, ShotOut, StoryBibleOut
from app.services.studio_service import StudioService
router = APIRouter(prefix="/api/projects", tags=["projects"])

def svc(db: Session) -> StudioService: return StudioService(db)

def handle(fn):
    try: return fn()
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("", response_model=ProjectOut)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)): return svc(db).create_project(data)
@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)): return svc(db).list_projects()
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).get_project(project_id))
@router.post("/{project_id}/generate-story-bible", response_model=StoryBibleOut)
def generate_story_bible(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_story_bible(project_id))
@router.post("/{project_id}/generate-script", response_model=ScriptOut)
def generate_script(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_script(project_id))
@router.post("/{project_id}/generate-characters", response_model=list[CharacterOut])
def generate_characters(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_characters(project_id))
@router.post("/{project_id}/select-character", response_model=CharacterOut)
def select_character(project_id:int, data: SelectCharacterRequest, db: Session=Depends(get_db)): return handle(lambda: svc(db).select_character(project_id, data.character_id))
@router.post("/{project_id}/auto-select-characters", response_model=list[CharacterOut])
def auto_select_characters(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).auto_select_characters(project_id))
@router.post("/{project_id}/generate-assets", response_model=list[AssetOut])
def generate_assets(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_assets(project_id))
@router.post("/{project_id}/generate-shots", response_model=list[ShotOut])
def generate_shots(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_shots(project_id))
@router.post("/{project_id}/generate-all", response_model=ExportOut)
def generate_all(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).generate_all(project_id))
@router.post("/{project_id}/export", response_model=ExportOut)
def export_project(project_id:int, db: Session=Depends(get_db)): return handle(lambda: svc(db).export_project(project_id))
@router.get("/{project_id}/memory-anchors", response_model=list[MemoryAnchorOut])
def memory_anchors(project_id:int, db: Session=Depends(get_db)): return svc(db).memory_anchors(project_id)
@router.get("/{project_id}/continuity-reports", response_model=list[ContinuityReportOut])
def continuity_reports(project_id:int, db: Session=Depends(get_db)): return svc(db).continuity_reports(project_id)
