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
