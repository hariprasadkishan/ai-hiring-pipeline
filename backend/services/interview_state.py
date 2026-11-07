from typing import TypedDict, List, Dict, Any, Optional

class AgendaTopic(TypedDict, total=False):
    topic_id: str
    category: str
    description: str
    target_depth: str
    status: str

class TurnEvaluation(TypedDict, total=False):
    question_num: int
    topic_id: str
    question: str
    answer: str
    score: float
    feedback: str
    missing_points: List[str]

class InterviewState(TypedDict, total=False):
    session_id: str
    application_id: str
    candidate_name: str
    program_type: str
    department: str
    opening_title: str
    syllabus_topics: List[str]
    resume_text: str

    agenda_topics: List[AgendaTopic]
    max_questions: int
    current_question_index: int
    current_question: str

    latest_candidate_response: str
    candidate_intent: str
    transcript: List[Dict[str, str]]
    turn_evaluations: List[TurnEvaluation]

    integrity_violations: int
    tab_switch_count: int
    is_hard_timeout: bool
    termination_reason: Optional[str]

    final_evaluation_report: Optional[Dict[str, Any]]
    is_completed: bool
