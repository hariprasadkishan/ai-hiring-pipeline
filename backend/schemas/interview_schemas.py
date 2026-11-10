from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class StartInterviewRequest(BaseModel):
    application_id: str

class SubmitAnswerRequest(BaseModel):
    session_id: str
    candidate_response: str
    telemetry_data: Optional[Dict[str, Any]] = None  # Latency, tab switches, WPM

class InterviewMessageResponse(BaseModel):
    message_id: str
    sender: str
    question_num: int
    content: str
    turn_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InterviewTurnResponse(BaseModel):
    session_id: str
    status: str
    current_question_index: int
    total_questions: int
    current_question: Optional[str] = None
    last_turn_score: Optional[float] = None
    last_turn_feedback: Optional[str] = None
    is_completed: bool = False
    final_report: Optional[Dict[str, Any]] = None

class InterviewSessionDetailResponse(BaseModel):
    session_id: str
    application_id: str
    status: str
    total_questions: int
    current_question_index: int
    overall_score: Optional[float] = None
    evaluation_report: Optional[Dict[str, Any]] = None
    messages: List[InterviewMessageResponse] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InterviewSlotResponse(BaseModel):
    slot_id: str
    opening_id: str
    start_time: datetime
    end_time: datetime
    is_booked: bool
    confirmation_code: Optional[str] = None

    class Config:
        from_attributes = True

class BookInterviewSlotRequest(BaseModel):
    slot_id: str
    application_id: str

class BookingConfirmationResponse(BaseModel):
    message: str
    confirmation_code: str
    slot_id: str
    application_id: str
    start_time: datetime
    end_time: datetime
    mock_calendar_event: Dict[str, Any]

class IdentityVerificationRequest(BaseModel):
    application_id: str
    live_frame: str  # Base64 data URL or raw base64 string
    reference_photo: Optional[str] = None  # Base64 data URL or raw base64 string
    check_type: Optional[str] = "ENTRY_HARD_GATE"

class IdentityVerificationResponse(BaseModel):
    passed: bool
    status: str
    confidence: float
    faces_detected: int
    action: str
    reason: str
    log_file: Optional[str] = None

class IdentityStatusResponse(BaseModel):
    application_id: str
    passed: bool
    status: str
    confidence: Optional[float] = None
    reason: Optional[str] = None

class TranscribeAudioResponse(BaseModel):
    text: str
    source: str = "whisper"

class TurnReasoningItem(BaseModel):
    question_num: int
    competency: Optional[str] = None
    decision: Optional[str] = None
    trigger_phrase_from_candidate: Optional[str] = None
    reasoning: Optional[str] = None
    question_asked: Optional[str] = None
    score: Optional[float] = None

class FinalRecommendationCandidate(BaseModel):
    rank: int
    application_id: str
    student_id: str
    candidate_name: str
    candidate_email: str
    gpa: float
    resume_score: float
    interview_score: Optional[float] = None
    composite_score: float
    status: str
    recommendation: str  # RECOMMENDED, BORDERLINE, REJECTED, PENDING_INTERVIEW
    competency_scores: Dict[str, float] = {}
    verdict_rationale: str
    evidence_summary: Optional[Dict[str, Any]] = None
    turn_reasoning_logs: List[TurnReasoningItem] = []

class FinalRecommendationReport(BaseModel):
    opening_id: str
    opening_title: str
    total_candidates: int
    completed_interviews: int
    ranked_candidates: List[FinalRecommendationCandidate]


