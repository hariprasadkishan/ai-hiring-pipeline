import json
import asyncio
from openai import OpenAI, AsyncOpenAI
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
from models.opening import AdmissionOpening

llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async_llm_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = (
    "You are an expert AI recruiting and candidate assessment evaluator for high-rigor engineering roles and graduate admissions. "
    "Always return valid raw JSON strictly adhering to the requested schema without markdown formatting or code blocks."
)

COMPETENCY_DEFINITIONS = {
    "technical_depth": "Technical Depth & Core Fundamentals: Deep understanding of computer science / engineering principles.",
    "system_architecture": "System Architecture & Engineering Rigor: Scalable designs, system patterns, and clean engineering practices.",
    "problem_solving": "Problem Solving & Algorithmic Thinking: Analytical capability to deconstruct and solve complex challenges.",
    "communication": "Communication & Professional Articulation: Clarity, structure, and conciseness in explaining concepts.",
    "leadership_mentorship": "Leadership, Mentorship & Initiative: Guiding peers, taking ownership, and driving technical direction.",
    "adaptability": "Adaptability & Continuous Learning: Agility in acquiring new tools, frameworks, and pivoting across stacks.",
    "domain_expertise": "Domain Alignment & Relevance: Direct domain match with target role requirements, research, and tools.",
    "collaboration": "Collaboration & Teamwork: Cross-functional coordination, code review rigor, and team synergy.",
    "analytical_reasoning": "Analytical Reasoning & Trade-off Analysis: Balancing performance, cost, and architectural constraints.",
    "delivery_reliability": "Professional Integrity & Delivery Reliability: Consistent track record of production-grade delivery and honesty."
}

def _build_evaluation_prompt(resume_text: str, opening: AdmissionOpening) -> str:
    return f"""
You are an expert technical evaluator assessing a candidate's resume for the role: "{opening.title}" ({opening.program_type}, {opening.department}).
Opening Requirements / Job Description:
- Department: {opening.department}
- Scope / Overview: {opening.description or 'N/A'}
- Target Domains: {', '.join(opening.research_areas or [])}
- Preferred Tools / Skills: {', '.join(opening.preferred_skills or [])}
- Core Prerequisites: {', '.join(opening.prerequisites or [])}
- Focus Topics: {', '.join(opening.syllabus_topics or [])}

Candidate Resume Text:
{resume_text[:16000]}

Perform two comprehensive tasks:
1. STRUCTURED PROFILE EXTRACTION:
Extract candidate name, contact email, phone, education list, technical skills list, and brief career experience.

2. 10 PREDEFINED COMPETENCIES EVALUATION:
Score each of the following 10 competencies on a scale of 0.0 to 10.0 based strictly on verifiable evidence in the resume.
For EACH competency, provide:
- "score": number between 0.0 and 10.0
- "evidence": Direct quote or specific factual excerpt from the resume (or "No direct evidence provided in resume" if missing)
- "analysis": 1-2 sentence objective justification

The 10 Competencies:
1. technical_depth: Technical Depth & Core Fundamentals
2. system_architecture: System Architecture & Engineering Rigor
3. problem_solving: Problem Solving & Algorithmic Thinking
4. communication: Communication & Professional Articulation
5. leadership_mentorship: Leadership, Mentorship & Initiative
6. adaptability: Adaptability & Continuous Learning
7. domain_expertise: Domain Alignment & Relevance
8. collaboration: Collaboration & Teamwork
9. analytical_reasoning: Analytical Reasoning & Trade-off Analysis
10. delivery_reliability: Professional Integrity & Delivery Reliability

The overall "resume_score" MUST be the exact sum of all 10 competency scores (ranging from 0.0 to 100.0).

Return ONLY valid JSON matching this schema:
{{
  "resume_score": <sum of 10 competency scores between 0.0 and 100.0>,
  "extracted_profile": {{
    "candidate_name": "<name>",
    "contact_email": "<email>",
    "contact_phone": "<phone>",
    "education": ["<degree/institution>"],
    "skills": ["<skill1>", "<skill2>"],
    "experience_summary": "<brief summary>"
  }},
  "competencies": {{
    "technical_depth": {{"score": 8.0, "evidence": "<quote>", "analysis": "<reason>"}},
    "system_architecture": {{"score": 7.5, "evidence": "<quote>", "analysis": "<reason>"}},
    "problem_solving": {{"score": 8.5, "evidence": "<quote>", "analysis": "<reason>"}},
    "communication": {{"score": 7.0, "evidence": "<quote>", "analysis": "<reason>"}},
    "leadership_mentorship": {{"score": 6.5, "evidence": "<quote>", "analysis": "<reason>"}},
    "adaptability": {{"score": 8.0, "evidence": "<quote>", "analysis": "<reason>"}},
    "domain_expertise": {{"score": 8.5, "evidence": "<quote>", "analysis": "<reason>"}},
    "collaboration": {{"score": 7.5, "evidence": "<quote>", "analysis": "<reason>"}},
    "analytical_reasoning": {{"score": 8.0, "evidence": "<quote>", "analysis": "<reason>"}},
    "delivery_reliability": {{"score": 8.0, "evidence": "<quote>", "analysis": "<reason>"}}
  }},
  "matching_skills": ["<matched skill 1>", "<matched skill 2>"],
  "missing_skills": ["<gap 1>", "<gap 2>"],
  "summary_reasoning": "<2-3 sentence executive evaluation justifying score>"
}}
"""

def _clean_json_content(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    return content

async def evaluate_resume_with_llm_async(
    resume_text: str,
    opening: AdmissionOpening,
    max_retries: int = 1
) -> dict:
    """
    Asynchronously evaluates candidate resume text against Opening JD criteria via OpenRouter AI.
    Includes exponential backoff retry for rate limits and transient errors.
    """
    prompt = _build_evaluation_prompt(resume_text, opening)

    for attempt in range(max_retries + 1):
        try:
            response = await async_llm_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                timeout=15.0
            )

            raw_content = response.choices[0].message.content
            cleaned = _clean_json_content(raw_content)
            parsed = json.loads(cleaned)

            # Ensure resume_score is valid float
            score = float(parsed.get("resume_score", 60.0))
            parsed["resume_score"] = max(0.0, min(100.0, round(score, 1)))

            # Populate backward-compatible score_breakdown if needed
            if "score_breakdown" not in parsed:
                parsed["score_breakdown"] = {
                    "prerequisites_score": round((parsed["resume_score"] / 100.0) * 35.0, 1),
                    "research_alignment_score": round((parsed["resume_score"] / 100.0) * 30.0, 1),
                    "technical_skills_score": round((parsed["resume_score"] / 100.0) * 20.0, 1),
                    "projects_achievements_score": round((parsed["resume_score"] / 100.0) * 15.0, 1),
                }
            return parsed

        except Exception as e:
            if attempt < max_retries:
                backoff_time = 1.5 * (attempt + 1)
                print(f"[LLM Evaluator Async] Attempt {attempt + 1} failed: {e}. Retrying in {backoff_time}s...")
                await asyncio.sleep(backoff_time)
            else:
                print(f"[LLM Evaluator Async] Evaluation failed after {max_retries + 1} attempts: {e}")
                default_comp = {
                    k: {"score": 6.0, "evidence": "Evaluated baseline", "analysis": "Assigned baseline score."}
                    for k in COMPETENCY_DEFINITIONS
                }
                return {
                    "resume_score": 60.0,
                    "competencies": default_comp,
                    "extracted_profile": {
                        "candidate_name": "Applicant",
                        "education": [],
                        "skills": [],
                        "experience_summary": "Extracted from candidate submission."
                    },
                    "score_breakdown": {
                        "prerequisites_score": 20.0,
                        "research_alignment_score": 18.0,
                        "technical_skills_score": 12.0,
                        "projects_achievements_score": 10.0
                    },
                    "matching_skills": [],
                    "missing_skills": [],
                    "summary_reasoning": f"Baseline assigned due to evaluation fallback ({str(e)})."
                }

def evaluate_resume_with_llm(resume_text: str, opening: AdmissionOpening) -> dict:
    """
    Synchronous fallback for evaluate_resume_with_llm.
    """
    prompt = _build_evaluation_prompt(resume_text, opening)

    try:
        response = llm_client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=15.0
        )

        raw_content = response.choices[0].message.content
        cleaned = _clean_json_content(raw_content)
        parsed = json.loads(cleaned)

        score = float(parsed.get("resume_score", 60.0))
        parsed["resume_score"] = max(0.0, min(100.0, round(score, 1)))
        if "score_breakdown" not in parsed:
            parsed["score_breakdown"] = {
                "prerequisites_score": round((parsed["resume_score"] / 100.0) * 35.0, 1),
                "research_alignment_score": round((parsed["resume_score"] / 100.0) * 30.0, 1),
                "technical_skills_score": round((parsed["resume_score"] / 100.0) * 20.0, 1),
                "projects_achievements_score": round((parsed["resume_score"] / 100.0) * 15.0, 1),
            }
        return parsed

    except Exception as e:
        print(f"[LLM Evaluator Sync] OpenRouter Evaluation Error: {e}")
        default_comp = {
            k: {"score": 6.0, "evidence": "Evaluated baseline", "analysis": "Assigned baseline score."}
            for k in COMPETENCY_DEFINITIONS
        }
        return {
            "resume_score": 60.0,
            "competencies": default_comp,
            "extracted_profile": {
                "candidate_name": "Applicant",
                "education": [],
                "skills": [],
                "experience_summary": "Extracted from candidate submission."
            },
            "score_breakdown": {
                "prerequisites_score": 20.0,
                "research_alignment_score": 18.0,
                "technical_skills_score": 12.0,
                "projects_achievements_score": 10.0
            },
            "matching_skills": [],
            "missing_skills": [],
            "summary_reasoning": f"Default baseline assigned due to evaluation error ({str(e)})."
        }
