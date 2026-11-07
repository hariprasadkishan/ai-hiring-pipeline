import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.interview import InterviewSession, InterviewMessage, InterviewSessionStatus, MessageSender
from models.application import Application
from models.user import StudentProfile, User
from models.opening import AdmissionOpening
from schemas.interview import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    InterviewTurnResponse,
    InterviewSessionDetailResponse,
    InterviewMessageResponse,
)
from services.interview_agent import interview_agent_graph
from services.interview_state import InterviewState


def _reconstruct_state_from_session(
    session: InterviewSession,
    application: Application,
    opening: AdmissionOpening,
    candidate_name: str
) -> InterviewState:
    """Reconstructs the InterviewState dictionary from DB session records."""
    eval_report = session.evaluation_report or {}
    agenda = eval_report.get("agenda_topics", [])
    
    # Load transcript and evaluations from messages
    messages = session.messages or []
    messages_sorted = sorted(messages, key=lambda m: m.created_at)
    
    transcript = []
    turn_evaluations = []
    current_q = None

    for m in messages_sorted:
        sender_role = "AI" if m.sender == MessageSender.AI else "CANDIDATE"
        transcript.append({"role": sender_role, "content": m.content})
        if m.sender == MessageSender.AI:
            current_q = m.content
        elif m.sender == MessageSender.CANDIDATE and m.turn_score is not None:
            turn_evaluations.append({
                "question_num": m.question_num,
                "question": current_q or "",
                "answer": m.content,
                "score": m.turn_score,
                "feedback": m.turn_feedback.get("feedback", "") if isinstance(m.turn_feedback, dict) else str(m.turn_feedback or ""),
                "missing_points": m.turn_feedback.get("missing_points", []) if isinstance(m.turn_feedback, dict) else []
            })

    state: InterviewState = {
        "session_id": session.session_id,
        "application_id": application.application_id,
        "candidate_name": candidate_name,
        "program_type": opening.program_type,
        "department": opening.department,
        "opening_title": opening.title,
        "syllabus_topics": opening.syllabus_topics or [],
        "resume_text": str(application.resume_feedback or ""),
        "agenda_topics": agenda,
        "max_questions": session.total_questions,
        "current_question_index": session.current_question_index,
        "current_question": current_q or "",
        "latest_candidate_response": "",
        "candidate_intent": "ANSWER",
        "transcript": transcript,
        "turn_evaluations": turn_evaluations,
        "integrity_violations": 0,
        "tab_switch_count": 0,
        "is_hard_timeout": False,
        "termination_reason": session.termination_reason,
        "final_evaluation_report": eval_report.get("final_evaluation_report"),
        "is_completed": session.status == InterviewSessionStatus.COMPLETED,
    }
    return state


def start_interview_session(db: Session, request: StartInterviewRequest, current_user: dict) -> InterviewTurnResponse:
    """Initializes or resumes an interactive LangGraph interview session for a candidate."""
    application = db.query(Application).filter(Application.application_id == request.application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    student = db.query(StudentProfile).filter(StudentProfile.student_id == application.student_id).first()
    user = db.query(User).filter(User.user_id == student.user_id).first() if student else None

    # Check authorization: user must be the candidate or faculty
    if current_user["role"] == "student" and (not student or student.user_id != current_user["user_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this interview.")

    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == application.opening_id).first()
    if not opening:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission opening not found.")

    # Check for existing session
    existing_session = db.query(InterviewSession).filter(InterviewSession.application_id == application.application_id).first()

    if existing_session:
        # Resume existing session
        last_ai_message = (
            db.query(InterviewMessage)
            .filter(InterviewMessage.session_id == existing_session.session_id, InterviewMessage.sender == MessageSender.AI)
            .order_by(InterviewMessage.created_at.desc())
            .first()
        )
        last_eval_msg = (
            db.query(InterviewMessage)
            .filter(InterviewMessage.session_id == existing_session.session_id, InterviewMessage.sender == MessageSender.CANDIDATE)
            .order_by(InterviewMessage.created_at.desc())
            .first()
        )

        return InterviewTurnResponse(
            session_id=existing_session.session_id,
            status=existing_session.status.value,
            current_question_index=existing_session.current_question_index,
            total_questions=existing_session.total_questions,
            current_question=last_ai_message.content if last_ai_message else None,
            last_turn_score=last_eval_msg.turn_score if last_eval_msg else None,
            last_turn_feedback=last_eval_msg.turn_feedback.get("feedback") if last_eval_msg and isinstance(last_eval_msg.turn_feedback, dict) else None,
            is_completed=existing_session.status == InterviewSessionStatus.COMPLETED,
            final_report=existing_session.evaluation_report
        )

    # Create new session
    new_session = InterviewSession(
        application_id=application.application_id,
        status=InterviewSessionStatus.IN_PROGRESS,
        total_questions=5,
        current_question_index=0,
        started_at=datetime.datetime.utcnow(),
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Initialize graph state
    candidate_name = user.name if user else "Candidate"
    initial_state: InterviewState = {
        "session_id": new_session.session_id,
        "application_id": application.application_id,
        "candidate_name": candidate_name,
        "program_type": opening.program_type,
        "department": opening.department,
        "opening_title": opening.title,
        "syllabus_topics": opening.syllabus_topics or [],
        "resume_text": str(application.resume_feedback or ""),
        "transcript": [],
        "turn_evaluations": [],
        "integrity_violations": 0,
        "tab_switch_count": 0,
        "is_hard_timeout": False,
        "is_completed": False
    }

    # Run LangGraph from ingest_context -> plan_agenda -> generate_question -> END
    state_result = interview_agent_graph.invoke(initial_state)

    first_question = state_result.get("current_question", "")

    # Save initial question
    first_msg = InterviewMessage(
        session_id=new_session.session_id,
        sender=MessageSender.AI,
        question_num=1,
        content=first_question,
    )
    db.add(first_msg)

    # Save agenda in session evaluation_report
    new_session.evaluation_report = {"agenda_topics": state_result.get("agenda_topics", [])}
    db.commit()

    return InterviewTurnResponse(
        session_id=new_session.session_id,
        status=new_session.status.value,
        current_question_index=0,
        total_questions=new_session.total_questions,
        current_question=first_question,
        last_turn_score=None,
        last_turn_feedback=None,
        is_completed=False,
        final_report=None
    )


def submit_candidate_answer(db: Session, request: SubmitAnswerRequest, current_user: dict) -> InterviewTurnResponse:
    """Submits candidate answer turn, evaluates response, and advances the state machine graph."""
    session = db.query(InterviewSession).filter(InterviewSession.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    if session.status == InterviewSessionStatus.COMPLETED:
        return InterviewTurnResponse(
            session_id=session.session_id,
            status=session.status.value,
            current_question_index=session.current_question_index,
            total_questions=session.total_questions,
            current_question=None,
            is_completed=True,
            final_report=session.evaluation_report
        )

    application = db.query(Application).filter(Application.application_id == session.application_id).first()
    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == application.opening_id).first()
    student = db.query(StudentProfile).filter(StudentProfile.student_id == application.student_id).first()
    user = db.query(User).filter(User.user_id == student.user_id).first() if student else None

    # Reconstruct current graph state
    candidate_name = user.name if user else "Candidate"
    state = _reconstruct_state_from_session(session, application, opening, candidate_name)

    # Attach current candidate response & telemetry
    state["latest_candidate_response"] = request.candidate_response
    if request.telemetry_data:
        state["tab_switch_count"] = request.telemetry_data.get("tab_switches", 0)
        state["is_hard_timeout"] = request.telemetry_data.get("is_timeout", False)

    # Execute graph: perceive_evaluate -> router -> (generate_question OR clarify_question OR finalize_report)
    state_result = interview_agent_graph.invoke(state)

    # Save Candidate message with evaluation
    latest_eval = state_result.get("turn_evaluations", [])[-1] if state_result.get("turn_evaluations") else None
    
    cand_msg = InterviewMessage(
        session_id=session.session_id,
        sender=MessageSender.CANDIDATE,
        question_num=session.current_question_index + 1,
        content=request.candidate_response,
        turn_score=latest_eval["score"] if latest_eval else None,
        turn_feedback=latest_eval if latest_eval else {},
        telemetry_data=request.telemetry_data
    )
    db.add(cand_msg)

    # Update session progress
    session.current_question_index = state_result.get("current_question_index", session.current_question_index)

    # Handle completion or next question
    if state_result.get("is_completed"):
        session.status = InterviewSessionStatus.COMPLETED
        session.completed_at = datetime.datetime.utcnow()
        session.overall_score = state_result.get("final_evaluation_report", {}).get("overall_score")
        session.evaluation_report = state_result.get("final_evaluation_report")
        session.termination_reason = state_result.get("termination_reason", "AGENDA_COMPLETED")
        db.commit()

        return InterviewTurnResponse(
            session_id=session.session_id,
            status=session.status.value,
            current_question_index=session.current_question_index,
            total_questions=session.total_questions,
            current_question=None,
            last_turn_score=latest_eval["score"] if latest_eval else None,
            last_turn_feedback=latest_eval.get("feedback") if latest_eval else None,
            is_completed=True,
            final_report=session.evaluation_report
        )

    # Next question or clarification
    next_question = state_result.get("current_question", "")
    ai_msg = InterviewMessage(
        session_id=session.session_id,
        sender=MessageSender.AI,
        question_num=session.current_question_index + 1,
        content=next_question
    )
    db.add(ai_msg)
    db.commit()

    return InterviewTurnResponse(
        session_id=session.session_id,
        status=session.status.value,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        current_question=next_question,
        last_turn_score=latest_eval["score"] if latest_eval else None,
        last_turn_feedback=latest_eval.get("feedback") if latest_eval else None,
        is_completed=False,
        final_report=None
    )


def get_interview_session_details(db: Session, session_id: str, current_user: dict) -> InterviewSessionDetailResponse:
    """Fetches full session details, turn transcript, and evaluation report."""
    session = db.query(InterviewSession).filter(InterviewSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.created_at.asc())
        .all()
    )

    messages_response = [
        InterviewMessageResponse(
            message_id=m.message_id,
            sender=m.sender.value if hasattr(m.sender, "value") else str(m.sender),
            question_num=m.question_num,
            content=m.content,
            turn_score=m.turn_score,
            created_at=m.created_at
        )
        for m in messages
    ]

    return InterviewSessionDetailResponse(
        session_id=session.session_id,
        application_id=session.application_id,
        status=session.status.value,
        total_questions=session.total_questions,
        current_question_index=session.current_question_index,
        overall_score=session.overall_score,
        evaluation_report=session.evaluation_report,
        messages=messages_response,
        created_at=session.created_at,
        completed_at=session.completed_at
    )
