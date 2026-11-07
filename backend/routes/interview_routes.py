from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import get_current_user_data
from schemas import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    InterviewTurnResponse,
    InterviewSessionDetailResponse,
)
from controllers.interview_controller import (
    start_interview_session,
    submit_candidate_answer,
    get_interview_session_details,
)

router = APIRouter(
    prefix="/api/interview",
    tags=["Academic AI Interview Agent"]
)

@router.post("/start", response_model=InterviewTurnResponse, status_code=status.HTTP_200_OK)
def start_interview(
    request: StartInterviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Initializes or resumes an interactive LangGraph interview session for a candidate."""
    return start_interview_session(db, request, current_user)


@router.post("/respond", response_model=InterviewTurnResponse, status_code=status.HTTP_200_OK)
def submit_response(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Submits candidate answer turn, evaluates response, and advances the state machine graph."""
    return submit_candidate_answer(db, request, current_user)


@router.get("/{session_id}", response_model=InterviewSessionDetailResponse, status_code=status.HTTP_200_OK)
def get_session_details(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Fetches full session details, turn transcript, and evaluation report."""
    return get_interview_session_details(db, session_id, current_user)