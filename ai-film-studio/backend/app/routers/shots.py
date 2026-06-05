from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.studio import ContinuityReportOut, MemoryAnchorOut, ShotOut, ShotPromptOut
from app.services.studio_service import StudioService
router = APIRouter(prefix="/api/shots", tags=["shots"])

def handle(fn):
    try: return fn()
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
@router.post("/{shot_id}/generate-prompt", response_model=ShotPromptOut)
def generate_prompt(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).generate_prompt(shot_id))
@router.post("/{shot_id}/generate-video")
def generate_video(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).generate_video(shot_id))
@router.post("/{shot_id}/extract-frames", response_model=ShotOut)
def extract_frames(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).extract_frames(shot_id))
@router.post("/{shot_id}/create-memory-anchor", response_model=MemoryAnchorOut)
def create_memory_anchor(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).create_memory_anchor(shot_id))
@router.post("/{shot_id}/review-continuity", response_model=ContinuityReportOut)
def review_continuity(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).review_continuity(shot_id))
@router.post("/{shot_id}/repair-and-retry", response_model=ContinuityReportOut)
def repair_and_retry(shot_id:int, db: Session=Depends(get_db)): return handle(lambda: StudioService(db).repair_and_retry(shot_id))
