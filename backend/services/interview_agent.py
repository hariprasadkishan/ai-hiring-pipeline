import json
import os
from openai import OpenAI
from langgraph.graph import StateGraph, END
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
from .interview_state import InterviewState, TurnEvaluation, AgendaTopic

# Shared OpenRouter LLM Client initialization
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=12.0,
    max_retries=1,
)
MODEL_NAME = OPENROUTER_MODEL or "google/gemini-2.0-flash-001"

PREDEFINED_COMPETENCIES = [
    "technical_depth",
    "system_architecture",
    "problem_solving",
    "communication",
    "leadership_mentorship",
    "adaptability",
    "domain_expertise",
    "collaboration",
    "analytical_reasoning",
    "delivery_reliability",
]


# ---------------------------------------------------------
# GRAPH NODES
# ---------------------------------------------------------

def ingest_context_node(state: InterviewState) -> InterviewState:
    """Entry node: Prepares context for agenda generation."""
    if not state.get("transcript"):
        state["transcript"] = []
    if not state.get("turn_evaluations"):
        state["turn_evaluations"] = []
    if "current_turn_count" not in state:
        state["current_turn_count"] = 0
    if "max_total_turns" not in state:
        state["max_total_turns"] = 8  # Dynamic turn ceiling
    if "malpractice_events" not in state:
        state["malpractice_events"] = []
    if "competencies_covered" not in state:
        state["competencies_covered"] = []
    return state


def plan_agenda_node(state: InterviewState) -> InterviewState:
    """Structures dynamic interview topics mapped to core competencies."""
    prereqs = ", ".join(state.get("prerequisites", [])) or "Core Fundamentals"
    skills = ", ".join(state.get("preferred_skills", [])) or "System Engineering & Architecture"

    agenda: list[AgendaTopic] = [
        {
            "topic_id": "c1",
            "category": "technical_depth",
            "description": f"Core Technical Depth, Runtime Mechanics & Theoretical Rigor ({prereqs})",
            "target_depth": "Deep",
            "status": "PENDING",
            "follow_up_count": 0,
            "max_follow_ups": 2,
            "mastery_score": 0.0,
        },
        {
            "topic_id": "c2",
            "category": "system_architecture",
            "description": f"System Architecture, Scalability & Engineering Tooling ({skills})",
            "target_depth": "High",
            "status": "PENDING",
            "follow_up_count": 0,
            "max_follow_ups": 2,
            "mastery_score": 0.0,
        },
        {
            "topic_id": "c3",
            "category": "problem_solving",
            "description": "Algorithmic Problem Solving, Edge Cases & Failure Diagnosis",
            "target_depth": "High",
            "status": "PENDING",
            "follow_up_count": 0,
            "max_follow_ups": 1,
            "mastery_score": 0.0,
        },
        {
            "topic_id": "c4",
            "category": "delivery_reliability",
            "description": "Production Delivery, Testing Rigor, CI/CD & Operational Reliability",
            "target_depth": "High",
            "status": "PENDING",
            "follow_up_count": 0,
            "max_follow_ups": 1,
            "mastery_score": 0.0,
        },
        {
            "topic_id": "c5",
            "category": "domain_expertise",
            "description": "Specialized Domain Expertise, Novel Trade-offs & Research Innovations",
            "target_depth": "Deep",
            "status": "PENDING",
            "follow_up_count": 0,
            "max_follow_ups": 1,
            "mastery_score": 0.0,
        },
    ]

    state["agenda_topics"] = agenda
    state["max_questions"] = len(agenda)
    state["current_question_index"] = 0
    state["current_turn_count"] = 0
    state["competencies_covered"] = []
    return state


def generate_question_node(state: InterviewState) -> InterviewState:
    """
    Formulates spoken interview question adhering to agent decision:
    - If initial turn: welcomes candidate and introduces opening competency.
    - If question already decided by perceive_evaluate node (e.g. broad_pivot or narrow_follow_up), uses that question.
    - Otherwise formulates contextual opening for next competency topic.
    """
    idx = min(state["current_question_index"], len(state["agenda_topics"]) - 1)
    topic = state["agenda_topics"][idx]
    decision = state.get("decision", "next_competency")
    cand_name = state.get("candidate_name", "Candidate")
    opening_title = state.get("opening_title", "Technical Position")
    dept = state.get("department", "Engineering")
    is_initial_turn = (idx == 0 and len(state.get("transcript", [])) == 0)

    # If perceive_evaluate already formulated a dynamic question, use it directly
    if not is_initial_turn and state.get("question_asked"):
        question_text = state["question_asked"]
    elif is_initial_turn:
        prompt = f"""
You are an expert AI interviewer conducting a technical evaluation for: {opening_title} in {dept}.
Candidate Name: {cand_name}
Candidate Resume Summary: {state.get('resume_text', '')[:1000]}

Generate the spoken dialogue for opening this interview adhering to this structure:
1. GREETING: Welcome {cand_name} to the technical interview.
2. ORIENTATION: Explain that this is an interactive voice interview where questions adapt dynamically based on their answers, probing technical claims and leadership experiences.
3. OPENING QUESTION (Competency: {topic['category']}):
   Ask {cand_name} to introduce themselves and highlight the most technically complex engineering project they built, detailing the core architecture and difficult technical hurdles they solved.

Speak in a natural, authoritative yet encouraging voice. Return ONLY the spoken dialogue without any headers, markdown, or quotes so it can be synthesized directly to speech.
"""
        try:
            response = llm_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                timeout=15.0,
            )
            question_text = response.choices[0].message.content.strip().replace('"', '')
<<<<<<< HEAD
            if not question_text:
                raise ValueError("Empty LLM response for initial question")
=======
>>>>>>> origin/main
        except Exception:
            question_text = (
                f"Hello {cand_name}, welcome to your technical interview for {opening_title} in {dept}. "
                f"This is an interactive voice interview evaluated across key competencies. "
                f"To begin, please introduce yourself and walk us through the most technically demanding project you have engineered, "
                f"focusing on your direct architectural choices and how you solved the hardest technical challenges."
            )
    else:
        # Generate question for next planned competency
        prompt = f"""
You are an expert technical interviewer conducting an interview for {opening_title}.
Target Competency: {topic['category']} - {topic['description']}
Resume Excerpt: {state.get('resume_text', '')[:800]}
Previous dialogue context:
{json.dumps(state.get('transcript', [])[-4:])}

Formulate a sharp, engaging question to assess the candidate's {topic['category']}.
Connect it with practical engineering scenarios, trade-offs, or their stated background.
Return ONLY the question text without quotes or pleasantries.
"""
        try:
            response = llm_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                timeout=15.0,
            )
            question_text = response.choices[0].message.content.strip().replace('"', '')
<<<<<<< HEAD
            if not question_text:
                raise ValueError("Empty LLM response for competency question")
        except Exception:
            question_text = f"Moving to {topic['category']}: Could you explain a scenario where you had to apply {topic['description']} in a production environment?"

    if not question_text or not question_text.strip():
        question_text = f"Could you walk us through your technical experience with {topic['description']}?"

=======
        except Exception:
            question_text = f"Moving to {topic['category']}: Could you explain a scenario where you had to apply {topic['description']} in a production environment?"

>>>>>>> origin/main
    state["current_question"] = question_text
    state["transcript"].append({"role": "AI", "content": question_text})
    state["current_turn_count"] = state.get("current_turn_count", 0) + 1
    state["agenda_topics"][idx]["status"] = "IN_PROGRESS"
    return state


def perceive_evaluate_node(state: InterviewState) -> InterviewState:
    """
    Reasoning-Driven Deliberation Node.
    Evaluates candidate answer semantically and chooses between:
    1. narrow_follow_up
    2. broad_pivot
    3. next_competency
    4. conclude

    Always logs:
    - trigger_phrase_from_candidate
    - reasoning
    - decision
    - question_asked
    """
    response_text = state.get("latest_candidate_response", "").strip()
    state["transcript"].append({"role": "CANDIDATE", "content": response_text})

    idx = min(state["current_question_index"], len(state["agenda_topics"]) - 1)
    current_q = state["current_question"]
    topic = state["agenda_topics"][idx]
    current_competency = topic.get("category", "technical_depth")
    follow_ups_done = topic.get("follow_up_count", 0)
    max_follow_ups = topic.get("max_follow_ups", 2)
    turns_count = len(state.get("turn_evaluations", [])) + 1
    max_turns = state.get("max_total_turns", 5)
    covered_comps = state.get("competencies_covered", [])


    prompt = f"""
You are an advanced reasoning AI technical interviewer evaluating a candidate's response.

INTERVIEW CONTEXT:
- Opening: {state.get('opening_title')} ({state.get('department')})
- Current Question: "{current_q}"
- Current Competency Assessed: {current_competency}
- Candidate Response: "{response_text}"
- Turn Count: {turns_count} of {max_turns} maximum turns.
- Competencies already covered: {json.dumps(covered_comps)}
- 10 Predefined Competencies: {json.dumps(PREDEFINED_COMPETENCIES)}

YOUR TASK:
1. Semantically analyze the candidate's answer for depth, accuracy, evidence, and emergent topics.
2. Select EXACTLY ONE of the four agentic decisions:
   a) "narrow_follow_up":
      Use when the candidate made a specific technical claim, architecture choice, or left an important mechanism/trade-off unexplained on the current competency.
      Identify the exact phrase that warrants probing, and ask a targeted follow-up question digging into the mechanics, constraints, or trade-offs.
   b) "broad_pivot":
      Use when the candidate's response introduces or touches on a NEW competency not yet deeply covered (e.g. candidate says "I also mentored two junior developers" -> pivot to leadership_mentorship; candidate says "I negotiated requirements with product managers" -> pivot to communication or collaboration; candidate says "we pivoted from REST to gRPC after benchmarking" -> pivot to problem_solving or adaptability).
      Identify the exact trigger phrase, recognize the emergent competency, and formulate an original question exploring it.
   c) "next_competency":
      Use when the candidate has adequately answered the current question (score >= 70) or the follow-up budget for this topic is met. Move to the next key competency on the agenda.
   d) "conclude":
      Use when the candidate has covered all major competencies or the turn budget ({turns_count} >= {max_turns}) is exhausted.

3. Calculate an evidence-based score for this turn (0.0 to 100.0).

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON object matching this schema:
{{
  "decision": "narrow_follow_up" | "broad_pivot" | "next_competency" | "conclude",
  "trigger_phrase_from_candidate": "exact quote or phrase from candidate response that caused this decision",
  "reasoning": "detailed 2-3 sentence semantic reasoning explaining why this decision was made",
  "question_asked": "the precise next interview question to be spoken to the candidate",
  "emergent_competency": "one of the 10 predefined competencies if broad_pivot, else null",
  "score": 85.0,
  "competency_assessed": "{current_competency}",
  "feedback": "constructive 1-2 sentence feedback on candidate's answer",
  "missing_points": ["missing point 1", "missing point 2"]
}}
"""
    try:
        response = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=15.0,
        )
        cleaned = response.choices[0].message.content.strip()
        eval_data = json.loads(cleaned)
    except Exception as e:
        print(f"[Interview Agent] LLM Deliberation exception: {e}")
        # Robust fallback deliberation
        has_mentorship = "mentor" in response_text.lower() or "junior" in response_text.lower() or "lead" in response_text.lower()
        if has_mentorship and "leadership_mentorship" not in covered_comps:
            eval_data = {
                "decision": "broad_pivot",
                "trigger_phrase_from_candidate": "mentored junior developers" if "mentor" in response_text.lower() else "leadership experience",
                "reasoning": "Candidate highlighted mentorship and guidance of peers. Pivoting to explore leadership and mentorship competency.",
                "question_asked": "You mentioned mentoring others in your engineering role. Could you walk us through how you guided junior engineers through technical challenges and code reviews?",
                "emergent_competency": "leadership_mentorship",
                "score": 78.0,
                "competency_assessed": "leadership_mentorship",
                "feedback": "Demonstrated technical initiative and mentorship awareness.",
                "missing_points": []
            }
        elif follow_ups_done < max_follow_ups:
            eval_data = {
                "decision": "narrow_follow_up",
                "trigger_phrase_from_candidate": response_text[:80] + "...",
                "reasoning": "Candidate provided a high-level overview. Probing deeper into architectural constraints and error handling.",
                "question_asked": f"Regarding your explanation: how did you handle edge cases, error conditions, and concurrency in that implementation?",
                "emergent_competency": None,
                "score": 72.0,
                "competency_assessed": current_competency,
                "feedback": "Good foundational response; investigating depth.",
                "missing_points": ["Concurrency considerations", "Failure recovery"]
            }
        else:
            eval_data = {
                "decision": "next_competency",
                "trigger_phrase_from_candidate": response_text[:80] + "...",
                "reasoning": "Topic satisfactorily evaluated. Advancing to next evaluation competency.",
                "question_asked": "Let us examine your approach to distributed system architecture and scalability.",
                "emergent_competency": None,
                "score": 75.0,
                "competency_assessed": current_competency,
                "feedback": "Satisfactory competency demonstration.",
                "missing_points": []
            }

    decision = eval_data.get("decision", "next_competency")
    trigger_phrase = eval_data.get("trigger_phrase_from_candidate", "")
    reasoning = eval_data.get("reasoning", "")
<<<<<<< HEAD
    question_asked = (eval_data.get("question_asked") or "").strip()
=======
    question_asked = eval_data.get("question_asked", "")
>>>>>>> origin/main
    emergent_competency = eval_data.get("emergent_competency")
    score = float(eval_data.get("score", 70.0))
    comp_assessed = eval_data.get("competency_assessed", current_competency)

    # Force conclude if hard turn budget reached
    if turns_count >= max_turns:
        decision = "conclude"
        reasoning += f" (Reached maximum interview turn budget of {max_turns} turns)."
        question_asked = "Thank you for answering our questions today. That concludes our interview session."
<<<<<<< HEAD
    elif not question_asked:
        if decision == "broad_pivot":
            question_asked = f"Regarding {emergent_competency or 'your recent comment'}: could you explain your direct contributions and technical decisions?"
        elif decision == "narrow_follow_up":
            question_asked = f"Could you elaborate on the architecture, trade-offs, and failure handling behind '{trigger_phrase or current_competency}'?"
        else:
            question_asked = f"Moving forward, how would you approach the engineering challenges involved in {topic.get('description', current_competency)}?"
=======
>>>>>>> origin/main

    state["decision"] = decision
    state["agentic_action"] = decision
    state["trigger_phrase_from_candidate"] = trigger_phrase
    state["reasoning"] = reasoning
    state["probe_rationale"] = reasoning
    state["question_asked"] = question_asked
    state["emergent_competency"] = emergent_competency

    if comp_assessed not in state.get("competencies_covered", []):
        state.setdefault("competencies_covered", []).append(comp_assessed)

    # Turn evaluation logging
    turn_eval: TurnEvaluation = {
        "question_num": turns_count,
        "topic_id": topic["topic_id"],
        "category": topic["category"],
        "competency": comp_assessed,
        "question": current_q,
        "answer": response_text,
        "score": score,
        "action_taken": decision,
        "decision": decision,
        "trigger_phrase_from_candidate": trigger_phrase,
        "reasoning": reasoning,
        "question_asked": question_asked,
        "feedback": eval_data.get("feedback", ""),
        "missing_points": eval_data.get("missing_points", []),
    }
    state["turn_evaluations"].append(turn_eval)
    topic["mastery_score"] = score

    # Dynamic agenda adaptation
    if decision == "narrow_follow_up":
        topic["follow_up_count"] = follow_ups_done + 1
        # Stay on current topic index
    elif decision == "broad_pivot":
        # Insert or prioritize emergent competency in agenda
        if emergent_competency:
            state.setdefault("competencies_covered", []).append(emergent_competency)
            new_topic: AgendaTopic = {
                "topic_id": f"piv_{len(state['agenda_topics'])+1}",
                "category": emergent_competency,
                "description": f"Emergent Competency: {emergent_competency.replace('_', ' ').title()}",
                "target_depth": "High",
                "status": "IN_PROGRESS",
                "follow_up_count": 0,
                "max_follow_ups": 1,
                "mastery_score": score,
            }
            state["agenda_topics"].append(new_topic)
            state["max_questions"] = len(state["agenda_topics"])
            state["current_question_index"] = len(state["agenda_topics"]) - 1
    elif decision == "next_competency":
        topic["status"] = "MASTERED" if score >= 75.0 else "COVERED"
        state["current_question_index"] += 1
    elif decision == "conclude":
        topic["status"] = "COVERED"
        state["termination_reason"] = "AGENDA_COMPLETED"

    # Termination triggers
    if state.get("integrity_violations", 0) >= 3 or state.get("tab_switch_count", 0) > 4:
        state["termination_reason"] = "INTEGRITY_VIOLATION"
    elif state.get("is_hard_timeout"):
        state["termination_reason"] = "HARD_TIMEOUT"
    elif len(state.get("turn_evaluations", [])) >= 3 and all(e["score"] == 0.0 for e in state.get("turn_evaluations", [])[-3:]):
        state["termination_reason"] = "CONSECUTIVE_ZERO_SCORES"
    elif turns_count >= max_turns or state["current_question_index"] >= len(state["agenda_topics"]):
        state["termination_reason"] = "AGENDA_COMPLETED"

    return state


def clarify_question_node(state: InterviewState) -> InterviewState:
    """Clarifies question without penalty."""
    current_q = state["current_question"]
    student_msg = state["latest_candidate_response"]

    prompt = f"""
The candidate asked for clarification during an interview.
Question: "{current_q}"
Candidate Query: "{student_msg}"

Provide a concise, helpful clarification (1-2 sentences) without answering the question or giving away solutions.
Return ONLY the clarification text.
"""
    try:
        response = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=15.0,
        )
        clarification = response.choices[0].message.content.strip().replace('"', '')
    except Exception:
        clarification = f"To clarify: Please focus on the fundamental concepts and practical trade-offs regarding '{current_q}'."

    state["current_question"] = clarification
    state["transcript"].append({"role": "AI", "content": clarification})
    return state


def finalize_report_node(state: InterviewState) -> InterviewState:
    """
    Stage 5 Final Recommendation Engine:
    - Synthesizes interview performance across all 10 predefined competencies.
    - Evaluates overall interview score.
    - Identifies evidence-backed strengths and weaknesses.
    - Formulates hiring recommendation (RECOMMENDED, BORDERLINE, REJECTED).
    """
    evals = state.get("turn_evaluations", [])
    if evals:
        overall_score = sum(e["score"] for e in evals) / len(evals)
    else:
        overall_score = 0.0

    violations = state.get("integrity_violations", 0)
    tab_switches = state.get("tab_switch_count", 0)
    malpractice_events = state.get("malpractice_events", [])
    term_reason = state.get("termination_reason", "AGENDA_COMPLETED")

    prompt = f"""
You are the Lead Hiring Committee AI synthesizing the Stage 4 Voice Interview Report.
Candidate: {state.get('candidate_name')}
Opening: {state.get('opening_title')} ({state.get('department')})
Turn Evaluations with Reasoning Logs: {json.dumps(evals, indent=2)}
Integrity Telemetry: {violations} alerts, {tab_switches} tab switches.
Termination Reason: {term_reason}

Map candidate interview performance across the 10 Predefined Competencies:
1. technical_depth
2. system_architecture
3. problem_solving
4. communication
5. leadership_mentorship
6. adaptability
7. domain_expertise
8. collaboration
9. analytical_reasoning
10. delivery_reliability

Return ONLY a valid JSON object matching this schema:
{{
  "overall_score": {overall_score:.1f},
  "competency_scores": {{
    "technical_depth": 80.0,
    "system_architecture": 75.0,
    "problem_solving": 78.0,
    "communication": 85.0,
    "leadership_mentorship": 70.0,
    "adaptability": 72.0,
    "domain_expertise": 80.0,
    "collaboration": 75.0,
    "analytical_reasoning": 76.0,
    "delivery_reliability": 74.0
  }},
  "strengths": ["Strength 1 with evidence", "Strength 2 with evidence"],
  "weaknesses": ["Improvement area 1", "Improvement area 2"],
  "summary_reasoning": "Detailed 3-4 sentence comprehensive evaluation explaining merit, technical depth, and competency assessment.",
  "recommendation": "RECOMMENDED" // Choose: "RECOMMENDED", "BORDERLINE", or "REJECTED"
}}
"""
    try:
        response = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=15.0,
        )
        cleaned = response.choices[0].message.content.strip()
        report = json.loads(cleaned)
    except Exception as e:
        print(f"[Interview Agent] Report synthesis exception: {e}")
        comp_scores = {c: round(overall_score, 1) for c in PREDEFINED_COMPETENCIES}
        report = {
            "overall_score": round(overall_score, 1),
            "competency_scores": comp_scores,
            "strengths": [
                "Demonstrated sound understanding of core engineering fundamentals.",
                "Engaged actively in voice dialogue and articulated practical trade-offs.",
            ],
            "weaknesses": [
                "Could provide deeper quantitative metrics on system performance and scale.",
            ],
            "summary_reasoning": f"Candidate completed dynamic reasoning voice interview with an overall interview score of {round(overall_score, 1)}/100.",
            "recommendation": "RECOMMENDED" if overall_score >= 70.0 else ("BORDERLINE" if overall_score >= 50.0 else "REJECTED"),
        }

    # Override recommendation if integrity compromised
    if violations >= 3 or tab_switches > 4 or term_reason == "INTEGRITY_VIOLATION":
        report["recommendation"] = "REJECTED"
        report["summary_reasoning"] = f"Interview disqualified due to integrity violations: {violations} visual malpractice alerts, {tab_switches} tab switch infractions."

    state["final_evaluation_report"] = report
    state["is_completed"] = True
    return state


# ---------------------------------------------------------
# ROUTER & WORKFLOW REGISTRATION
# ---------------------------------------------------------

def should_continue(state: InterviewState) -> str:
    """Conditional edge router logic with agentic action handling."""
    if state.get("integrity_violations", 0) >= 3 or state.get("tab_switch_count", 0) > 4:
        state["termination_reason"] = "INTEGRITY_VIOLATION"
        return "finalize_report"

    if state.get("is_hard_timeout"):
        state["termination_reason"] = "HARD_TIMEOUT"
        return "finalize_report"

    if state.get("decision") == "conclude":
        return "finalize_report"

    if state.get("agentic_action") == "CLARIFY" or state.get("candidate_intent") == "CLARIFICATION_REQUEST":
        return "clarify_question"

    completed_turns = len(state.get("turn_evaluations", []))
    max_turns = state.get("max_total_turns", 5)
    if completed_turns >= max_turns:
        state["termination_reason"] = "TURN_CEILING_REACHED"
        return "finalize_report"

    if state["current_question_index"] >= len(state.get("agenda_topics", [])):
        state["termination_reason"] = "AGENDA_COMPLETED"
        return "finalize_report"

    return "generate_question"



def route_from_ingest(state: InterviewState) -> str:
    """Routes to perceive_evaluate if candidate answered, or plan_agenda if starting fresh."""
    if state.get("integrity_violations", 0) >= 3 or state.get("tab_switch_count", 0) > 4 or state.get("is_hard_timeout"):
        return "finalize_report"
    if state.get("latest_candidate_response"):
        return "perceive_evaluate"
    if not state.get("agenda_topics"):
        return "plan_agenda"
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

workflow.add_conditional_edges(
    "ingest_context",
    route_from_ingest,
    {
        "plan_agenda": "plan_agenda",
        "perceive_evaluate": "perceive_evaluate",
        "generate_question": "generate_question",
        "finalize_report": "finalize_report",
    },
)

workflow.add_edge("plan_agenda", "generate_question")
workflow.add_edge("generate_question", END)

workflow.add_conditional_edges(
    "perceive_evaluate",
    should_continue,
    {
        "generate_question": "generate_question",
        "clarify_question": "clarify_question",
        "finalize_report": "finalize_report",
    },
)

workflow.add_edge("clarify_question", END)
workflow.add_edge("finalize_report", END)

interview_agent_graph = workflow.compile()
