from typing import Optional
from fastapi import APIRouter, Depends, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from utils.dependencies import get_current_user_data
from controllers.application_controller import (
    apply_for_opening,
    get_student_applications,
    stream_application_resume,
)

router = APIRouter(prefix="/api/applications", tags=["Student Applications"])

@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def submit_application(
    opening_id: str = Form(...),
    gpa: float = Form(...),
    gate_score: Optional[float] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return await apply_for_opening(
        opening_id=opening_id,
        gpa=gpa,
        gate_score=gate_score,
        resume=resume,
        db=db,
        current_user=current_user,
    )

@router.get("/student/my-applications")
def list_student_applications(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return get_student_applications(db, current_user)

@router.get("/{application_id}/resume", tags=["Faculty Evaluation"])
def view_resume(
    application_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return stream_application_resume(application_id, token, db)
