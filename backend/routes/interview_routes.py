from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import get_current_user_data
from schemas import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    InterviewTurnResponse,
    InterviewSessionDetailResponse,
    InterviewSlotResponse,
    BookInterviewSlotRequest,
    BookingConfirmationResponse,
    IdentityVerificationRequest,
    IdentityVerificationResponse,
    IdentityStatusResponse,
    TranscribeAudioResponse,
    FinalRecommendationReport,
)
from controllers.interview_controller import (
    start_interview_session,
    submit_candidate_answer,
    get_interview_session_details,
    get_available_slots,
    book_slot,
    get_application_booking,
    verify_candidate_identity,
    get_identity_status,
    transcribe_audio_speech,
    get_final_recommendations_for_opening,
)

router = APIRouter(
    prefix="/api/interview",
    tags=["Academic AI Interview Agent"]
)

# ---------------------------------------------------------------------------
# STAGE 2: SCHEDULING ENDPOINTS
# ---------------------------------------------------------------------------

@router.get("/slots/{opening_id}", response_model=list[InterviewSlotResponse], status_code=status.HTTP_200_OK)
def list_available_slots(
    opening_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Retrieves available interview slots for an opening."""
    return get_available_slots(db, opening_id, current_user)

@router.post("/slots/book", response_model=BookingConfirmationResponse, status_code=status.HTTP_200_OK)
def book_interview_slot(
    request: BookInterviewSlotRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Atomically books an interview slot and returns confirmation with mock calendar event."""
    return book_slot(db, request, current_user)

@router.get("/booking/{application_id}", response_model=BookingConfirmationResponse, status_code=status.HTTP_200_OK)
def get_booking_details(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Retrieves existing booking and calendar confirmation for an application."""
    return get_application_booking(db, application_id, current_user)

# ---------------------------------------------------------------------------
# STAGE 3: IDENTITY VERIFICATION (HARD GATE)
# ---------------------------------------------------------------------------

@router.post("/verify-identity", response_model=IdentityVerificationResponse, status_code=status.HTTP_200_OK)
def verify_identity(
    request: IdentityVerificationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """
    Stage 3 Mandatory Interview-Entry Gate:
    Compares live webcam frame against reference photo, detects faces, checks confidence,
    and writes timestamped audit trail to identity_log_<application_id>.json.
    """
    return verify_candidate_identity(request, db, current_user)

@router.get("/identity-status/{application_id}", response_model=IdentityStatusResponse, status_code=status.HTTP_200_OK)
def check_identity_status(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Retrieves Stage 3 identity gate verification status for an application."""
    return get_identity_status(application_id, db, current_user)

# ---------------------------------------------------------------------------
# STAGE 4: REASONING VOICE INTERVIEW & SPEECH-TO-TEXT
# ---------------------------------------------------------------------------

@router.post("/transcribe", response_model=TranscribeAudioResponse, status_code=status.HTTP_200_OK)
def transcribe_speech(
    audio_file: Optional[UploadFile] = File(None),
    transcript: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user_data)
):
    """Speech-to-text endpoint supporting Whisper model and client dictation fallback."""
    return transcribe_audio_speech(audio_file=audio_file, text_transcript=transcript)

@router.post("/start", response_model=InterviewTurnResponse, status_code=status.HTTP_200_OK)
def start_interview(
    request: StartInterviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Initializes or resumes an interactive LangGraph interview session for a candidate (Gated by Stage 3)."""
    return start_interview_session(db, request, current_user)

@router.post("/respond", response_model=InterviewTurnResponse, status_code=status.HTTP_200_OK)
def submit_response(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Submits candidate answer turn, evaluates response, and advances the dynamic state machine graph."""
    return submit_candidate_answer(db, request, current_user)

@router.get("/{session_id}", response_model=InterviewSessionDetailResponse, status_code=status.HTTP_200_OK)
def get_session_details(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """Fetches full session details, turn transcript, and evaluation report."""
    return get_interview_session_details(db, session_id, current_user)

# ---------------------------------------------------------------------------
# STAGE 5: FINAL RECOMMENDATIONS & COHORT RANKING
# ---------------------------------------------------------------------------

@router.get("/final-recommendations/{opening_id}", response_model=FinalRecommendationReport, status_code=status.HTTP_200_OK)
def get_final_recommendations(
    opening_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    """
    Stage 5 Final Recommendation Engine:
    Combines Stage 1 resume scores with Stage 4 dynamic interview scores across
    the 10 predefined competencies and produces a final ranked shortlist.
    """
    return get_final_recommendations_for_opening(db, opening_id, current_user)
