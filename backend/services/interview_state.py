from typing import TypedDict, List, Dict, Any, Optional

class AgendaTopic(TypedDict, total=False):
    topic_id: str
    category: str
    description: str
    target_depth: str
    status: str             # "PENDING" | "IN_PROGRESS" | "MASTERED" | "COVERED"
    follow_up_count: int    # Number of follow-up questions asked on this topic
    max_follow_ups: int     # Dynamic budget of follow-ups allowed (e.g., 2)
    mastery_score: float    # Aggregated or latest score for this topic

class TurnEvaluation(TypedDict, total=False):
    question_num: int
    topic_id: str
    category: str
    competency: str
    question: str
    answer: str
    score: float
    action_taken: str       # Backward compatible with older views
    decision: str           # "narrow_follow_up" | "broad_pivot" | "next_competency" | "conclude"
    trigger_phrase_from_candidate: str
    reasoning: str
    question_asked: str
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
    prerequisites: List[str]
    preferred_skills: List[str]
    research_areas: List[str]
    resume_text: str

    agenda_topics: List[AgendaTopic]
    competencies_covered: List[str]
    max_questions: int             # Total planned agenda topics
    current_question_index: int    # Current active agenda topic index
    current_turn_count: int        # Cumulative interview turns asked
    max_total_turns: int           # Hard ceiling across all turns (e.g., 9)
    current_question: str

    latest_candidate_response: str
    candidate_intent: str          # "ANSWER" | "CLARIFICATION_REQUEST" | "OFF_TOPIC"
    agentic_action: str            # "narrow_follow_up" | "broad_pivot" | "next_competency" | "conclude" | "CLARIFY"
    trigger_phrase_from_candidate: str
    reasoning: str
    decision: str
    question_asked: str
    emergent_competency: Optional[str]
    probe_rationale: str           # Backward compatible alias for reasoning
    transcript: List[Dict[str, str]]
    turn_evaluations: List[TurnEvaluation]

    integrity_violations: int
    tab_switch_count: int
    is_hard_timeout: bool
    malpractice_events: List[Dict[str, Any]]
    termination_reason: Optional[str]

    final_evaluation_report: Optional[Dict[str, Any]]
    is_completed: bool
