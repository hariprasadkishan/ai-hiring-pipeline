import json
import os
from openai import OpenAI
from langgraph.graph import StateGraph, END
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
from .interview_state import InterviewState, TurnEvaluation

# Shared OpenRouter LLM Client initialization
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
MODEL_NAME = OPENROUTER_MODEL or "google/gemini-2.0-flash-001"


# ---------------------------------------------------------
# GRAPH NODES
# ---------------------------------------------------------

def ingest_context_node(state: InterviewState) -> InterviewState:
    """Entry node: Prepares context for agenda generation."""
    if not state.get("transcript"):
        state["transcript"] = []
    if not state.get("turn_evaluations"):
        state["turn_evaluations"] = []
    return state


def plan_agenda_node(state: InterviewState) -> InterviewState:
    """Structures dynamic 5-question interview tree based on degree level."""
    program = state.get("program_type", "MTech")
    
    if program == "PhD":
        agenda = [
            {"topic_id": "t1", "category": "BACKGROUND", "description": "Research Experience & Publication/Thesis Defense", "target_depth": "High", "status": "PENDING"},
            {"topic_id": "t2", "category": "PREREQUISITES", "description": "Core Theoretical Foundations & Mathematics", "target_depth": "High", "status": "PENDING"},
            {"topic_id": "t3", "category": "RESEARCH_DEPTH", "description": "Domain Literature & Specific Research Methodology", "target_depth": "Deep", "status": "PENDING"},
            {"topic_id": "t4", "category": "PROBLEM_SOLVING", "description": "Open-Ended Problem Formulation & System Design", "target_depth": "Deep", "status": "PENDING"},
            {"topic_id": "t5", "category": "PROBING", "description": "Novel Contribution & Feasibility Defense", "target_depth": "Deep", "status": "PENDING"},
        ]
    else:  # MTech
        agenda = [
            {"topic_id": "t1", "category": "BACKGROUND", "description": "Academic Projects & Practical Stack Verification", "target_depth": "Medium", "status": "PENDING"},
            {"topic_id": "t2", "category": "PREREQUISITES", "description": "Core Syllabus Prerequisites & Fundamental Theory", "target_depth": "High", "status": "PENDING"},
            {"topic_id": "t3", "category": "RESEARCH_DEPTH", "description": "Applied Domain Knowledge & Tooling Mastery", "target_depth": "High", "status": "PENDING"},
            {"topic_id": "t4", "category": "PROBLEM_SOLVING", "description": "Algorithmic Scenario & Implementation Trade-offs", "target_depth": "High", "status": "PENDING"},
            {"topic_id": "t5", "category": "PROBING", "description": "Targeted Follow-up on Identified Knowledge Gaps", "target_depth": "High", "status": "PENDING"},
        ]

    state["agenda_topics"] = agenda
    state["max_questions"] = len(agenda)
    state["current_question_index"] = 0
    return state


def generate_question_node(state: InterviewState) -> InterviewState:
    """Generates next question using active agenda topic, resume facts, and past performance."""
    idx = state["current_question_index"]
    topic = state["agenda_topics"][idx]
    
    past_feedback = ""
    if state["turn_evaluations"]:
        last_eval = state["turn_evaluations"][-1]
        past_feedback = f"Previous Question Score: {last_eval['score']}/100. Evaluator Note: {last_eval['feedback']}"

    prompt = f"""
You are an expert academic interviewer conducting an interview for an admissions opening.
Opening Title: {state.get('opening_title')}
Degree Program: {state.get('program_type')} ({state.get('department')})
Syllabus Topics: {", ".join(state.get('syllabus_topics', []))}
Candidate Resume Excerpt: {state.get('resume_text', '')[:1000]}

Current Agenda Step ({idx + 1}/{state['max_questions']}): {topic['category']} - {topic['description']}
{past_feedback}

Formulate a clear, direct academic interview question targeting this specific agenda step.
If the candidate performed well in the previous turn, increase difficulty. If they struggled, ask a targeted diagnostic question.
Return ONLY the question text. Do not add introductions or meta text.
"""
    response = llm_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    question_text = response.choices[0].message.content.strip()
    state["current_question"] = question_text
    state["transcript"].append({"role": "AI", "content": question_text})
    state["agenda_topics"][idx]["status"] = "IN_PROGRESS"
    return state


def perceive_evaluate_node(state: InterviewState) -> InterviewState:
    """Evaluates candidate response against ground-truth domain expectations and checks intent."""
    response_text = state.get("latest_candidate_response", "").strip()
    state["transcript"].append({"role": "CANDIDATE", "content": response_text})
    
    idx = state["current_question_index"]
    current_q = state["current_question"]
    topic = state["agenda_topics"][idx]

    prompt = f"""
You are evaluating a candidate's response in an academic admission interview.
Question Asked: "{current_q}"
Candidate Response: "{response_text}"

Evaluate the response and output a JSON object with this EXACT structure:
{{
  "intent": "ANSWER",  // Choose: "ANSWER", "CLARIFICATION_REQUEST", or "OFF_TOPIC"
  "score": 85.0,        // Float between 0.0 and 100.0 (0.0 if clarification request or completely wrong)
  "feedback": "Short evaluation note explaining score.",
  "missing_points": ["Point 1", "Point 2"]
}}
Return ONLY valid JSON.
"""
    response = llm_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    try:
        cleaned = response.choices[0].message.content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:-3].strip()
        eval_data = json.loads(cleaned)
    except Exception:
        eval_data = {
            "intent": "ANSWER",
            "score": 50.0,
            "feedback": "Response recorded. Evaluation fallback triggered.",
            "missing_points": []
        }

    state["candidate_intent"] = eval_data.get("intent", "ANSWER")

    if state["candidate_intent"] == "ANSWER":
        turn_eval: TurnEvaluation = {
            "question_num": idx + 1,
            "topic_id": topic["topic_id"],
            "question": current_q,
            "answer": response_text,
            "score": float(eval_data.get("score", 50.0)),
            "feedback": eval_data.get("feedback", ""),
            "missing_points": eval_data.get("missing_points", [])
        }
        state["turn_evaluations"].append(turn_eval)
        state["agenda_topics"][idx]["status"] = "COVERED"
        state["current_question_index"] += 1

    return state


def clarify_question_node(state: InterviewState) -> InterviewState:
    """Clarifies question without advancing question index or penalizing candidate."""
    current_q = state["current_question"]
    student_msg = state["latest_candidate_response"]

    prompt = f"""
The candidate asked for clarification during an interview.
Question: "{current_q}"
Candidate Query: "{student_msg}"

Provide a helpful, non-giveaway clarification of the question. Keep it concise.
"""
    response = llm_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    
    clarification = response.choices[0].message.content.strip()
    state["current_question"] = clarification
    state["transcript"].append({"role": "AI", "content": clarification})
    return state


def finalize_report_node(state: InterviewState) -> InterviewState:
    """Aggregates scores and produces candidate evaluation report."""
    evals = state.get("turn_evaluations", [])
    if evals:
        overall_score = sum(e["score"] for e in evals) / len(evals)
    else:
        overall_score = 0.0

    prompt = f"""
Synthesize an executive academic assessment report for candidate {state.get('candidate_name')}.
Degree: {state.get('program_type')} ({state.get('department')})
Turn Evaluations: {json.dumps(evals)}

Return ONLY a valid JSON object with this EXACT structure:
{{
  "overall_score": {overall_score:.1f},
  "technical_depth_score": {overall_score:.1f},
  "problem_solving_score": {overall_score:.1f},
  "domain_knowledge_score": {overall_score:.1f},
  "communication_score": {overall_score:.1f},
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "summary_reasoning": "Detailed narrative evaluation for faculty panel.",
  "recommendation": "RECOMMENDED"  // Choose: "RECOMMENDED", "BORDERLINE", or "REJECTED"
}}
"""
    response = llm_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    try:
        cleaned = response.choices[0].message.content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:-3].strip()
        report = json.loads(cleaned)
    except Exception:
        report = {
            "overall_score": overall_score,
            "summary_reasoning": "Interview completed. Score calculated from turn evaluations.",
            "recommendation": "BORDERLINE"
        }

    state["final_evaluation_report"] = report
    state["is_completed"] = True
    return state


# ---------------------------------------------------------
# ROUTER & WORKFLOW REGISTRATION
# ---------------------------------------------------------

def should_continue(state: InterviewState) -> str:
    """Conditional edge router logic."""
    if state.get("integrity_violations", 0) >= 2 or state.get("tab_switch_count", 0) > 3:
        state["termination_reason"] = "INTEGRITY_VIOLATION"
        return "finalize_report"

    if state.get("is_hard_timeout"):
        state["termination_reason"] = "HARD_TIMEOUT"
        return "finalize_report"

    if state.get("candidate_intent") == "CLARIFICATION_REQUEST":
        return "clarify_question"

    # Consecutive failed turns stop early
    recent_evals = state.get("turn_evaluations", [])[-2:]
    if len(recent_evals) == 2 and all(e["score"] == 0.0 for e in recent_evals):
        state["termination_reason"] = "CONSECUTIVE_ZERO_SCORES"
        return "finalize_report"

    if state["current_question_index"] >= state["max_questions"]:
        state["termination_reason"] = "AGENDA_COMPLETED"
        return "finalize_report"

    return "generate_question"


# Compile Graph
workflow = StateGraph(InterviewState)

workflow.add_node("ingest_context", ingest_context_node)
workflow.add_node("plan_agenda", plan_agenda_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("perceive_evaluate", perceive_evaluate_node)
workflow.add_node("clarify_question", clarify_question_node)
workflow.add_node("finalize_report", finalize_report_node)

workflow.set_entry_point("ingest_context")

workflow.add_edge("ingest_context", "plan_agenda")
workflow.add_edge("plan_agenda", "generate_question")
workflow.add_edge("generate_question", END)  # Pauses execution for candidate answer

workflow.add_conditional_edges(
    "perceive_evaluate",
    should_continue,
    {
        "generate_question": "generate_question",
        "clarify_question": "clarify_question",
        "finalize_report": "finalize_report"
    }
)

workflow.add_edge("clarify_question", END)  # Pauses for answer after clarification
workflow.add_edge("finalize_report", END)

interview_agent_graph = workflow.compile()