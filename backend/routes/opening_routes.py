from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas import OpeningCreateSchema, EvaluateResumesSchema
from utils.dependencies import get_current_user_data
from controllers.opening_controller import (
    create_opening,
    get_teacher_openings,
    get_student_openings,
)
from controllers.application_controller import (
    get_opening_applicants,
    evaluate_and_shortlist_candidates,
)

router = APIRouter(prefix="/api/openings", tags=["Admission Openings"])

@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_new_opening(
    payload: OpeningCreateSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return create_opening(payload, db, current_user)

@router.get("/teacher")
def list_teacher_openings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return get_teacher_openings(db, current_user)

@router.get("/student", tags=["Student Openings"])
def list_student_openings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return get_student_openings(db, current_user)

@router.get("/{opening_id}/applicants", tags=["Faculty Evaluation"])
def list_applicants(
    opening_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return get_opening_applicants(opening_id, db, current_user)

@router.post("/{opening_id}/evaluate-resumes", tags=["Faculty Evaluation"])
def evaluate_candidates(
    opening_id: str,
    payload: EvaluateResumesSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return evaluate_and_shortlist_candidates(opening_id, payload, db, current_user)
