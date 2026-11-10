import datetime
import uuid
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.interview import (
    InterviewSession,
    InterviewMessage,
    InterviewSessionStatus,
    MessageSender,
    InterviewSlot,
)
from models.application import Application
from models.user import StudentProfile, User
from models.opening import AdmissionOpening
from schemas.interview import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    InterviewTurnResponse,
    InterviewSessionDetailResponse,
    InterviewMessageResponse,
    InterviewSlotResponse,
    BookInterviewSlotRequest,
    BookingConfirmationResponse,
    IdentityVerificationRequest,
    IdentityVerificationResponse,
    IdentityStatusResponse,
    TranscribeAudioResponse,
    FinalRecommendationCandidate,
    FinalRecommendationReport,
    TurnReasoningItem,
)
from services.interview_agent import interview_agent_graph, PREDEFINED_COMPETENCIES, llm_client
from services.interview_state import InterviewState
from services.face_verification_service import perform_identity_verification, LOGS_DIR
import json
import os


# ---------------------------------------------------------------------------
# STAGE 3: IDENTITY VERIFICATION HARD GATE HELPERS
# ---------------------------------------------------------------------------

def check_identity_gate_status(application_id: str) -> dict:
    """
    Checks identity_log_<id>.json to verify candidate has passed the Stage 3 Hard Gate.
    """
    filename = f"identity_log_{application_id}.json"
    app_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename))
    root_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", filename))
    logs_dir_path = os.path.join(LOGS_DIR, filename)

    target = None
    for p in [app_log_path, logs_dir_path, root_log_path]:
        if os.path.exists(p):
            target = p
            break

    if not target:
        return {
            "passed": False,
            "status": "NOT_VERIFIED",
            "confidence": 0.0,
            "reason": "Stage 3 Identity Verification (HARD GATE) not completed. Webcam face verification is required to start the interview."
        }


    try:
        with open(target, "r") as f:
            records = json.load(f)
            if not isinstance(records, list):
                records = [records]

            entry_records = [r for r in records if r.get("check_type") == "ENTRY_HARD_GATE"]
            latest = entry_records[-1] if entry_records else records[-1]
            result = latest.get("result", "FAIL")
            passed = (result == "PASS")
            return {
                "passed": passed,
                "status": result,
                "confidence": latest.get("match_confidence", 0.0),
                "reason": latest.get("reason", "Identity check completed.") if passed else latest.get("reason", "Face verification failed or uncertain. Routed to human review.")
            }
    except Exception as e:
        return {
            "passed": False,
            "status": "ERROR",
            "confidence": 0.0,
            "reason": f"Failed reading identity audit log: {str(e)}"
        }


def verify_candidate_identity(request: IdentityVerificationRequest, db: Session, current_user: dict) -> IdentityVerificationResponse:
    """
    Performs Stage 3 Identity Verification (HARD GATE).
    - Captures candidate through webcam
    - Compares live face against submitted reference photograph
    - Detects face presence and multiple faces
    - Calculates face matching confidence
    - Logs check to identity_log_<id>.json
    - Pass -> Allows interview entry
    - Fail or uncertain -> Blocks entry and routes to human review
    """
    application = db.query(Application).filter(Application.application_id == request.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    student = db.query(StudentProfile).filter(StudentProfile.student_id == application.student_id).first()
    if current_user["role"] == "student" and (not student or student.user_id != current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Unauthorized access to this application.")

    live_bytes = request.live_frame.encode("utf-8") if isinstance(request.live_frame, str) else request.live_frame
    ref_bytes = request.reference_photo.encode("utf-8") if request.reference_photo else None

    result = perform_identity_verification(
        live_image_bytes=live_bytes,
        reference_image_bytes=ref_bytes,
        application_id=request.application_id,
        check_type=request.check_type or "ENTRY_HARD_GATE"
    )

    return IdentityVerificationResponse(
        passed=result["passed"],
        status=result["status"],
        confidence=result["confidence"],
        faces_detected=result["faces_detected"],
        action=result["action"],
        reason=result["reason"],
        log_file=result.get("log_file")
    )


def get_identity_status(application_id: str, db: Session, current_user: dict) -> IdentityStatusResponse:
    """Returns current Stage 3 Identity Verification status for an application."""
    application = db.query(Application).filter(Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    status_data = check_identity_gate_status(application_id)
    return IdentityStatusResponse(
        application_id=application_id,
        passed=status_data["passed"],
        status=status_data["status"],
        confidence=status_data.get("confidence"),
        reason=status_data.get("reason")
    )


# ---------------------------------------------------------------------------
# STAGE 4: REASONING VOICE INTERVIEW GRAPH CONTROLLERS
# ---------------------------------------------------------------------------

def _reconstruct_state_from_session(
    session: InterviewSession,
    application: Application,
    opening: AdmissionOpening,
    candidate_name: str
) -> InterviewState:
    """Reconstructs the InterviewState dictionary from DB session records."""
    eval_report = session.evaluation_report or {}
    agenda = eval_report.get("agenda_topics", [])

    messages = session.messages or []
    messages_sorted = sorted(messages, key=lambda m: m.created_at)

    transcript = []
    turn_evaluations = []
    current_q = None
    malpractice_events = []
    total_violations = 0
    covered_comps = []

    for m in messages_sorted:
        sender_role = "AI" if m.sender == MessageSender.AI else "CANDIDATE"
        transcript.append({"role": sender_role, "content": m.content})
        if m.sender == MessageSender.AI:
            current_q = m.content
        elif m.sender == MessageSender.CANDIDATE:
            if m.turn_score is not None:
                fb = m.turn_feedback if isinstance(m.turn_feedback, dict) else {}
                comp = fb.get("competency", "technical_depth")
                if comp and comp not in covered_comps:
                    covered_comps.append(comp)

                turn_evaluations.append({
                    "question_num": m.question_num,
                    "topic_id": fb.get("topic_id", "c1"),
                    "category": fb.get("category", comp),
                    "competency": comp,
                    "question": current_q or "",
                    "answer": m.content,
                    "score": m.turn_score,
                    "action_taken": fb.get("decision", "next_competency"),
                    "decision": fb.get("decision", "next_competency"),
                    "trigger_phrase_from_candidate": fb.get("trigger_phrase_from_candidate", ""),
                    "reasoning": fb.get("reasoning", ""),
                    "question_asked": fb.get("question_asked", ""),
                    "feedback": fb.get("feedback", str(m.turn_feedback or "")),
                    "missing_points": fb.get("missing_points", []),
                })
            if m.telemetry_data and isinstance(m.telemetry_data, dict):
                events = m.telemetry_data.get("events", [])
                if isinstance(events, list):
                    malpractice_events.extend(events)
                total_violations += m.telemetry_data.get("violations_count", 0)

    state: InterviewState = {
        "session_id": session.session_id,
        "application_id": application.application_id,
        "candidate_name": candidate_name,
        "program_type": opening.program_type,
        "department": opening.department,
        "opening_title": opening.title,
        "syllabus_topics": opening.syllabus_topics or [],
        "prerequisites": opening.prerequisites or [],
        "preferred_skills": opening.preferred_skills or [],
        "research_areas": opening.research_areas or [],
        "resume_text": str(application.resume_feedback or ""),
        "agenda_topics": agenda,
        "competencies_covered": covered_comps,
        "max_questions": session.total_questions,
        "current_question_index": session.current_question_index,
        "current_turn_count": len(turn_evaluations),
        "max_total_turns": 5,
        "current_question": current_q or "",
        "latest_candidate_response": "",
        "candidate_intent": "ANSWER",
        "agentic_action": "next_competency",
        "decision": "next_competency",
        "trigger_phrase_from_candidate": "",
        "reasoning": "",
        "question_asked": "",
        "probe_rationale": "",
        "transcript": transcript,
        "turn_evaluations": turn_evaluations,
        "integrity_violations": total_violations,
        "tab_switch_count": 0,
        "is_hard_timeout": False,
        "malpractice_events": malpractice_events,
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
        # Fetch full message history for the existing session
        messages_db = (
            db.query(InterviewMessage)
            .filter(InterviewMessage.session_id == existing_session.session_id)
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
                turn_feedback=m.turn_feedback if isinstance(m.turn_feedback, dict) else None,
                created_at=m.created_at
            )
            for m in messages_db
        ]

        # STRICT CONSTRAINT: If completed or terminated, do NOT restart. Return the finalized session directly.
        if existing_session.status in [InterviewSessionStatus.COMPLETED, InterviewSessionStatus.TERMINATED_ABNORMALLY]:
            return InterviewTurnResponse(
                session_id=existing_session.session_id,
                status=existing_session.status.value,
                current_question_index=existing_session.current_question_index,
                total_questions=existing_session.total_questions,
                current_question=None,
                last_turn_score=None,
                last_turn_feedback=None,
                agentic_action="conclude",
                is_completed=True,
                final_report=existing_session.evaluation_report,
                messages=messages_response
            )

        # STAGE 3 HARD GATE: Verify identity check before resuming
        gate_status = check_identity_gate_status(application.application_id)
        if not gate_status["passed"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "IDENTITY_HARD_GATE_BLOCKED",
                    "message": gate_status.get("reason", "Stage 3 biometric verification is required before starting the interview."),
                    "identity_status": gate_status["status"],
                    "confidence": gate_status.get("confidence", 0.0),
                    "application_id": application.application_id,
                    "action": "ROUTE_TO_HUMAN_REVIEW" if gate_status["status"] in ["FAIL", "UNCERTAIN"] else "VERIFICATION_REQUIRED"
                }
            )

        # Resume existing in-progress session
        last_ai_message = next((m for m in reversed(messages_db) if m.sender == MessageSender.AI), None)
        last_eval_msg = next((m for m in reversed(messages_db) if m.sender == MessageSender.CANDIDATE), None)

        current_q = last_ai_message.content if last_ai_message else None
        if not current_q and existing_session.status == InterviewSessionStatus.IN_PROGRESS:
            current_q = (
                f"Hello {candidate_name}, welcome to your technical interview for {opening.title} in {opening.department}. "
                f"To begin, please introduce yourself and walk us through your most complex technical engineering project."
            )

        latest_feedback = last_eval_msg.turn_feedback if last_eval_msg and isinstance(last_eval_msg.turn_feedback, dict) else {}
        action = latest_feedback.get("decision", "next_competency")

        return InterviewTurnResponse(
            session_id=existing_session.session_id,
            status=existing_session.status.value,
            current_question_index=existing_session.current_question_index,
            total_questions=existing_session.total_questions,
            current_question=current_q,
            last_turn_score=last_eval_msg.turn_score if last_eval_msg else None,
            last_turn_feedback=latest_feedback.get("feedback") if latest_feedback else None,
            agentic_action=action,
            is_completed=False,
            final_report=existing_session.evaluation_report,
            messages=messages_response
        )

    # STRICT ONE-TIME CONSTRAINT: Check if application is already COMPLETED
    if application.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The interview for this application has already been concluded and cannot be retaken."
        )

    # STAGE 3 HARD GATE: Verify identity check before creating new session
    gate_status = check_identity_gate_status(application.application_id)
    if not gate_status["passed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "IDENTITY_HARD_GATE_BLOCKED",
                "message": gate_status.get("reason", "Stage 3 biometric verification is required before starting the interview."),
                "identity_status": gate_status["status"],
                "confidence": gate_status.get("confidence", 0.0),
                "application_id": application.application_id,
                "action": "ROUTE_TO_HUMAN_REVIEW" if gate_status["status"] in ["FAIL", "UNCERTAIN"] else "VERIFICATION_REQUIRED"
            }
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
        "prerequisites": opening.prerequisites or [],
        "preferred_skills": opening.preferred_skills or [],
        "research_areas": opening.research_areas or [],
        "resume_text": str(application.resume_feedback or ""),
        "transcript": [],
        "turn_evaluations": [],
        "integrity_violations": 0,
        "tab_switch_count": 0,
        "is_hard_timeout": False,
        "malpractice_events": [],
        "is_completed": False
    }

    # Run LangGraph from ingest_context -> plan_agenda -> generate_question -> END
    state_result = interview_agent_graph.invoke(initial_state)

    first_question = (state_result.get("current_question") or "").strip()
    if not first_question:
        first_question = (
            f"Hello {candidate_name}, welcome to your technical interview for {opening.title} in {opening.department}. "
            f"This is an interactive voice interview evaluated across key competencies. "
            f"To begin, please introduce yourself and walk us through the most technically demanding project you have engineered, "
            f"focusing on your direct architectural choices and how you solved the hardest technical challenges."
        )

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
    db.refresh(first_msg)

    first_msg_resp = InterviewMessageResponse(
        message_id=first_msg.message_id,
        sender="AI",
        question_num=1,
        content=first_question,
        turn_score=None,
        turn_feedback=None,
        created_at=first_msg.created_at
    )

    return InterviewTurnResponse(
        session_id=new_session.session_id,
        status=new_session.status.value,
        current_question_index=0,
        total_questions=new_session.total_questions,
        current_question=first_question,
        last_turn_score=None,
        last_turn_feedback=None,
        agentic_action="opening_question",
        is_completed=False,
        final_report=None,
        messages=[first_msg_resp]
    )


def submit_candidate_answer(db: Session, request: SubmitAnswerRequest, current_user: dict) -> InterviewTurnResponse:
    """Submits candidate answer turn, evaluates response, and advances the dynamic state machine graph."""
    session = db.query(InterviewSession).filter(InterviewSession.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    if session.status in [InterviewSessionStatus.COMPLETED, InterviewSessionStatus.TERMINATED_ABNORMALLY]:
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

    # Anti-swap frame analysis if camera frame is provided in telemetry
    if request.telemetry_data and "live_frame" in request.telemetry_data:
        frame_val = request.telemetry_data.get("live_frame")
        if frame_val and isinstance(frame_val, str):
            swap_res = perform_identity_verification(
                live_image_bytes=frame_val.encode("utf-8"),
                reference_image_bytes=None,
                application_id=session.application_id,
                check_type="ANTI_SWAP_CHECK"
            )
            if not swap_res["passed"]:
                if "events" not in request.telemetry_data:
                    request.telemetry_data["events"] = []
                request.telemetry_data["events"].append({
                    "type": "ANTI_SWAP_VIOLATION",
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "description": f"Anti-swap monitor alert: {swap_res['reason']}"
                })
                request.telemetry_data["violations_count"] = request.telemetry_data.get("violations_count", 0) + 1

    # Attach current candidate response & telemetry
    state["latest_candidate_response"] = request.candidate_response
    if request.telemetry_data:
        state["tab_switch_count"] = request.telemetry_data.get("tab_switches", 0)
        state["is_hard_timeout"] = request.telemetry_data.get("is_timeout", False)
        new_violations = request.telemetry_data.get("violations_count", 0)
        state["integrity_violations"] = state.get("integrity_violations", 0) + new_violations
        new_events = request.telemetry_data.get("events", [])
        if new_events and isinstance(new_events, list):
            state["malpractice_events"].extend(new_events)

    # Execute graph: perceive_evaluate -> should_continue -> (generate_question OR clarify_question OR finalize_report)
    state_result = interview_agent_graph.invoke(state)

    # Save Candidate message with full turn reasoning logs
    latest_eval = state_result.get("turn_evaluations", [])[-1] if state_result.get("turn_evaluations") else None

    cand_msg = InterviewMessage(
        session_id=session.session_id,
        sender=MessageSender.CANDIDATE,
        question_num=state_result.get("current_turn_count", session.current_question_index + 1),
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
        term_reason = state_result.get("termination_reason", "AGENDA_COMPLETED")
        if term_reason == "INTEGRITY_VIOLATION":
            session.status = InterviewSessionStatus.TERMINATED_ABNORMALLY
        else:
            session.status = InterviewSessionStatus.COMPLETED

        session.completed_at = datetime.datetime.utcnow()
        interview_score = float(state_result.get("final_evaluation_report", {}).get("overall_score") or 0.0)
        session.overall_score = interview_score

        # STAGE 5: Combine resume score (Stage 1) and interview score (Stage 4)
        resume_score = float(application.resume_score or 0.0)
        composite_score = round((resume_score * 0.40) + (interview_score * 0.60), 1)

        eval_report = state_result.get("final_evaluation_report", {}) or {}
        eval_report["stage5_composite"] = {
            "resume_score": resume_score,
            "interview_score": interview_score,
            "composite_score": composite_score,
            "weight_resume": 0.40,
            "weight_interview": 0.60,
        }
        session.evaluation_report = eval_report
        session.termination_reason = term_reason

        # Mark application as completed to enforce single-attempt lock
        if application:
            application.status = "COMPLETED"

        db.commit()

        messages_db = (
            db.query(InterviewMessage)
            .filter(InterviewMessage.session_id == session.session_id)
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
                turn_feedback=m.turn_feedback if isinstance(m.turn_feedback, dict) else None,
                created_at=m.created_at
            )
            for m in messages_db
        ]

        return InterviewTurnResponse(
            session_id=session.session_id,
            status=session.status.value,
            current_question_index=session.current_question_index,
            total_questions=session.total_questions,
            current_question=None,
            last_turn_score=latest_eval["score"] if latest_eval else None,
            last_turn_feedback=latest_eval.get("feedback") if latest_eval else None,
            agentic_action="conclude",
            is_completed=True,
            final_report=session.evaluation_report,
            messages=messages_response
        )

    # Next question or clarification
    next_question = (state_result.get("current_question") or "").strip()
    if not next_question:
        next_question = "Could you elaborate on the technical trade-offs and operational challenges you encountered in that implementation?"

    ai_msg = InterviewMessage(
        session_id=session.session_id,
        sender=MessageSender.AI,
        question_num=state_result.get("current_turn_count", session.current_question_index + 1),
        content=next_question
    )
    db.add(ai_msg)

    # Persist updated agenda topics in session evaluation_report
    agenda_saved = session.evaluation_report or {}
    agenda_saved["agenda_topics"] = state_result.get("agenda_topics", [])
    session.evaluation_report = agenda_saved
    db.commit()

    messages_db = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session.session_id)
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
            turn_feedback=m.turn_feedback if isinstance(m.turn_feedback, dict) else None,
            created_at=m.created_at
        )
        for m in messages_db
    ]

    action = state_result.get("decision", "next_competency")

    return InterviewTurnResponse(
        session_id=session.session_id,
        status=session.status.value,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        current_question=next_question,
        last_turn_score=latest_eval["score"] if latest_eval else None,
        last_turn_feedback=latest_eval.get("feedback") if latest_eval else None,
        agentic_action=action,
        is_completed=False,
        final_report=None,
        messages=messages_response
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


# ---------------------------------------------------------------------------
# STAGE 2: SCHEDULING CONTROLLERS
# ---------------------------------------------------------------------------

def _generate_default_slots_for_opening(db: Session, opening_id: str):
    """Generates standard calendar slots for an opening across upcoming business days."""
    now = datetime.datetime.utcnow()
    base_date = (now + datetime.timedelta(days=1)).replace(minute=0, second=0, microsecond=0)

    slot_offsets = [
        (1, 10, 0, 45),
        (1, 14, 0, 45),
        (1, 16, 0, 45),
        (2, 10, 0, 45),
        (2, 14, 0, 45),
        (2, 16, 0, 45),
        (3, 11, 0, 45),
        (3, 15, 0, 45),
    ]

    for day_offset, hour, start_min, duration_min in slot_offsets:
        start_time = (base_date + datetime.timedelta(days=day_offset)).replace(hour=hour, minute=start_min)
        end_time = start_time + datetime.timedelta(minutes=duration_min)
        slot = InterviewSlot(
            opening_id=opening_id,
            start_time=start_time,
            end_time=end_time,
            is_booked=False,
        )
        db.add(slot)
    db.commit()


def get_available_slots(db: Session, opening_id: str, current_user: dict) -> list[InterviewSlotResponse]:
    """Retrieves all available interview slots for an opening, generating them if none exist."""
    existing_slots = (
        db.query(InterviewSlot)
        .filter(InterviewSlot.opening_id == opening_id)
        .order_by(InterviewSlot.start_time.asc())
        .all()
    )

    if not existing_slots:
        _generate_default_slots_for_opening(db, opening_id)
        existing_slots = (
            db.query(InterviewSlot)
            .filter(InterviewSlot.opening_id == opening_id)
            .order_by(InterviewSlot.start_time.asc())
            .all()
        )

    return [
        InterviewSlotResponse(
            slot_id=s.slot_id,
            opening_id=s.opening_id,
            start_time=s.start_time,
            end_time=s.end_time,
            is_booked=s.is_booked,
            confirmation_code=s.confirmation_code
        )
        for s in existing_slots
    ]


def book_slot(db: Session, request: BookInterviewSlotRequest, current_user: dict) -> BookingConfirmationResponse:
    """Atomically books an interview slot for a shortlisted candidate, preventing double-booking race conditions."""
    application = db.query(Application).filter(Application.application_id == request.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    if application.status not in ["SHORTLISTED", "INTERVIEW_PENDING"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only shortlisted candidates can schedule an interview. Current status: {application.status}."
        )

    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == application.opening_id).first()

    # Double Booking Prevention 1: If application already has a booked slot, release it
    existing_booking = db.query(InterviewSlot).filter(InterviewSlot.booked_by_application_id == application.application_id).first()
    if existing_booking and existing_booking.slot_id == request.slot_id:
        return _build_confirmation_response(existing_booking, application, opening)
    elif existing_booking:
        existing_booking.is_booked = False
        existing_booking.booked_by_application_id = None
        existing_booking.confirmation_code = None

    # Double Booking Prevention 2: Atomic query with row-level lock
    slot = (
        db.query(InterviewSlot)
        .filter(InterviewSlot.slot_id == request.slot_id)
        .with_for_update()
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Requested interview slot not found.")

    if slot.is_booked:
        raise HTTPException(
            status_code=409,
            detail="This interview slot has just been booked by another candidate. Please select another slot."
        )

    # Confirm booking
    confirmation_code = f"CONF-{uuid.uuid4().hex[:8].upper()}"
    slot.is_booked = True
    slot.booked_by_application_id = application.application_id
    slot.confirmation_code = confirmation_code
    application.status = "INTERVIEW_PENDING"

    db.commit()
    db.refresh(slot)

    return _build_confirmation_response(slot, application, opening)


def _build_confirmation_response(slot: InterviewSlot, application: Application, opening: AdmissionOpening) -> BookingConfirmationResponse:
    """Constructs confirmation response and standard mock calendar event JSON."""
    opening_title = opening.title if opening else "Technical Interview"
    mock_calendar_event = {
        "event_id": f"cal_{slot.slot_id}",
        "summary": f"AI Technical Interview - {opening_title}",
        "description": f"Official automated AI voice interview session. Confirmation Code: {slot.confirmation_code}.",
        "start": slot.start_time.isoformat() + "Z",
        "end": slot.end_time.isoformat() + "Z",
        "status": "CONFIRMED",
        "location": "Virtual AI Interview Chamber",
        "attendees": [
            {"email": "candidate@portal.local", "role": "Candidate"},
            {"email": "ai-panel@agent.local", "role": "AI Technical Interviewer"}
        ],
        "meeting_link": f"http://localhost:3000/student/interview/{application.application_id}"
    }

    return BookingConfirmationResponse(
        message="Interview slot booked successfully.",
        confirmation_code=slot.confirmation_code or "CONF-ACTIVE",
        slot_id=slot.slot_id,
        application_id=application.application_id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        mock_calendar_event=mock_calendar_event
    )


def get_application_booking(db: Session, application_id: str, current_user: dict) -> BookingConfirmationResponse:
    """Fetches existing booking confirmation details for an application."""
    slot = db.query(InterviewSlot).filter(InterviewSlot.booked_by_application_id == application_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="No booked interview slot found for this application.")

    application = db.query(Application).filter(Application.application_id == application_id).first()
    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == application.opening_id).first() if application else None

    return _build_confirmation_response(slot, application, opening)


# ---------------------------------------------------------------------------
# STAGE 4: SPEECH-TO-TEXT TRANSCRIPTION (WHISPER)
# ---------------------------------------------------------------------------

def transcribe_audio_speech(audio_file=None, text_transcript: Optional[str] = None) -> TranscribeAudioResponse:
    """Speech transcription endpoint supporting Whisper API and real-time browser text dictation."""
    if text_transcript and text_transcript.strip():
        return TranscribeAudioResponse(text=text_transcript.strip(), source="browser_speech_to_text")

    if audio_file is not None:
        try:
            import io
            audio_bytes = audio_file.file.read()
            bio = io.BytesIO(audio_bytes)
            bio.name = audio_file.filename or "speech.wav"
            transcription = llm_client.audio.transcriptions.create(
                model="whisper-1",
                file=bio
            )
            return TranscribeAudioResponse(text=transcription.text, source="whisper-1")
        except Exception as e:
            print(f"[Whisper Transcribe] Exception: {e}")
            return TranscribeAudioResponse(text="", source="whisper_service_fallback")

    return TranscribeAudioResponse(text="", source="empty_input")


# ---------------------------------------------------------------------------
# STAGE 5: FINAL RECOMMENDATIONS & COHORT RANKING
# ---------------------------------------------------------------------------

def get_final_recommendations_for_opening(db: Session, opening_id: str, current_user: dict) -> FinalRecommendationReport:
    """
    Stage 5 Final Recommendation Engine:
    Combines Stage 1 resume scores & evidence with Stage 4 dynamic interview scores,
    evaluates all 10 predefined competencies, and produces a final ranked shortlist.
    """
    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    applications = (
        db.query(Application)
        .filter(Application.opening_id == opening_id)
        .all()
    )

    ranked_list = []
    completed_interviews = 0

    for app in applications:
        student = db.query(StudentProfile).filter(StudentProfile.student_id == app.student_id).first()
        user = db.query(User).filter(User.user_id == student.user_id).first() if student else None
        candidate_name = user.name if user else "Candidate"
        candidate_email = user.email if user else "candidate@portal.local"

        session = db.query(InterviewSession).filter(InterviewSession.application_id == app.application_id).first()
        resume_score = float(app.resume_score or 0.0)
        resume_feedback = app.resume_feedback or {}

        interview_score = None
        recommendation = "PENDING_INTERVIEW"
        verdict_rationale = "Candidate pending interview completion."
        comp_scores: Dict[str, float] = {}
        turn_logs: List[TurnReasoningItem] = []

        resume_comps = {}
        raw_comps = resume_feedback.get("competencies", {})
        if isinstance(raw_comps, dict):
            for k, v in raw_comps.items():
                if isinstance(v, dict) and "score" in v:
                    s = float(v["score"])
                    resume_comps[k] = s * 10.0 if s <= 10.0 else s
                elif isinstance(v, (int, float)):
                    resume_comps[k] = float(v) * 10.0 if float(v) <= 10.0 else float(v)

        if not resume_comps and isinstance(resume_feedback.get("competency_scores"), dict):
            resume_comps = resume_feedback.get("competency_scores", {})
        if not resume_comps and isinstance(resume_feedback.get("score_breakdown"), dict):
            resume_comps = resume_feedback.get("score_breakdown", {})


        if session and session.status in [InterviewSessionStatus.COMPLETED, InterviewSessionStatus.TERMINATED_ABNORMALLY]:
            completed_interviews += 1
            interview_score = float(session.overall_score or 0.0)
            composite_score = round((resume_score * 0.40) + (interview_score * 0.60), 1)

            eval_rep = session.evaluation_report or {}
            int_comp_scores = eval_rep.get("competency_scores", {})

            for comp in PREDEFINED_COMPETENCIES:
                r_val = float(resume_comps.get(comp, resume_score))
                i_val = float(int_comp_scores.get(comp, interview_score))
                comp_scores[comp] = round((r_val * 0.4) + (i_val * 0.6), 1)

            if session.status == InterviewSessionStatus.TERMINATED_ABNORMALLY or session.termination_reason == "INTEGRITY_VIOLATION":
                recommendation = "REJECTED"
                verdict_rationale = "Candidate disqualified due to proctoring / anti-swap integrity infractions."
            elif composite_score >= 72.0:
                recommendation = "RECOMMENDED"
                verdict_rationale = f"Strong demonstration across technical resume ({resume_score:.1f}) and voice interview ({interview_score:.1f})."
            elif composite_score >= 48.0:
                recommendation = "BORDERLINE"
                verdict_rationale = f"Adequate foundational competency ({composite_score:.1f}), with mixed responses during follow-up probing."
            else:
                recommendation = "REJECTED"
                verdict_rationale = f"Composite performance score ({composite_score:.1f}) does not meet competency thresholds."

            messages = (
                db.query(InterviewMessage)
                .filter(InterviewMessage.session_id == session.session_id, InterviewMessage.sender == MessageSender.CANDIDATE)
                .order_by(InterviewMessage.question_num.asc())
                .all()
            )
            for m in messages:
                fb = m.turn_feedback if isinstance(m.turn_feedback, dict) else {}
                turn_logs.append(TurnReasoningItem(
                    question_num=m.question_num,
                    competency=fb.get("competency", fb.get("category")),
                    decision=fb.get("decision", fb.get("action_taken")),
                    trigger_phrase_from_candidate=fb.get("trigger_phrase_from_candidate"),
                    reasoning=fb.get("reasoning", fb.get("feedback")),
                    question_asked=fb.get("question_asked"),
                    score=m.turn_score
                ))
        else:
            composite_score = round(resume_score * 0.40, 1)
            for comp in PREDEFINED_COMPETENCIES:
                comp_scores[comp] = round(float(resume_comps.get(comp, resume_score)), 1)
            verdict_rationale = f"Resume scored at {resume_score:.1f}. Awaiting Stage 4 voice interview evaluation."

        ranked_list.append(FinalRecommendationCandidate(
            rank=0,
            application_id=app.application_id,
            student_id=app.student_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            gpa=app.gpa,
            resume_score=resume_score,
            interview_score=interview_score,
            composite_score=composite_score,
            status=app.status,
            recommendation=recommendation,
            competency_scores=comp_scores,
            verdict_rationale=verdict_rationale,
            evidence_summary={
                "candidate_profile": resume_feedback.get("candidate_profile"),
                "competency_analysis": resume_feedback.get("competency_analysis"),
                "evidence_quotes": resume_feedback.get("evidence_quotes"),
            },
            turn_reasoning_logs=turn_logs
        ))

    # Sort descending by composite score (completed interviews first, then by score)
    ranked_list.sort(key=lambda c: (1 if c.interview_score is not None else 0, c.composite_score), reverse=True)

    # Assign sequential ranks
    for idx, cand in enumerate(ranked_list):
        cand.rank = idx + 1

    return FinalRecommendationReport(
        opening_id=opening.opening_id,
        opening_title=opening.title,
        total_candidates=len(ranked_list),
        completed_interviews=completed_interviews,
        ranked_candidates=ranked_list
    )
