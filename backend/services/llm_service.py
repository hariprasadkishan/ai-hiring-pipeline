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
    "You are a precise, fair academic resume evaluator for graduate admissions. "
    "Always return valid raw JSON strictly adhering to the requested schema without markdown formatting or code blocks."
)

def _build_evaluation_prompt(resume_text: str, opening: AdmissionOpening) -> str:
    return f"""
You are an expert academic admissions evaluator for graduate admissions ({opening.program_type}).
Evaluate the candidate's resume strictly against the opening's criteria using the following calibrated rubric:

EVALUATION RUBRIC (Total: 100 points):
1. Prerequisites & Syllabus Foundation (0 - 35 points):
   How thoroughly does the candidate cover the required core prerequisites and syllabus topics?
2. Research Domain Alignment (0 - 30 points):
   How strongly do the candidate's past research, thesis, publications, or domains align with target research areas?
3. Preferred Technical Skills & Tools (0 - 20 points):
   Does the candidate demonstrate hands-on competence with the preferred tools, libraries, and frameworks?
4. Academic Projects & Accomplishments (0 - 15 points):
   Quality of research projects, open-source work, academic standing, or notable accomplishments.

The final "resume_score" MUST be the sum of the breakdown categories (between 0.0 and 100.0).

Opening Criteria:
- Opening Title: {opening.title} ({opening.program_type})
- Department: {opening.department}
- Scope / Description: {opening.description or 'N/A'}
- Target Research Areas: {', '.join(opening.research_areas or [])}
- Preferred Skills: {', '.join(opening.preferred_skills or [])}
- Prerequisites: {', '.join(opening.prerequisites or [])}
- Syllabus Topics: {', '.join(opening.syllabus_topics or [])}

Candidate Resume Content:
{resume_text[:16000]}

Return ONLY a valid JSON object with this exact structure:
{{
  "resume_score": <number between 0.0 and 100.0>,
  "score_breakdown": {{
    "prerequisites_score": <number between 0.0 and 35.0>,
    "research_alignment_score": <number between 0.0 and 30.0>,
    "technical_skills_score": <number between 0.0 and 20.0>,
    "projects_achievements_score": <number between 0.0 and 15.0>
  }},
  "matching_skills": [<list of matched skills or domains>],
  "missing_skills": [<list of missing prerequisites or tools>],
  "summary_reasoning": "<2-3 sentence objective assessment justifying the score>"
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
    max_retries: int = 2
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
                temperature=0.2
            )

            raw_content = response.choices[0].message.content
            cleaned = _clean_json_content(raw_content)
            parsed = json.loads(cleaned)

            # Ensure resume_score is valid float
            score = float(parsed.get("resume_score", 60.0))
            parsed["resume_score"] = max(0.0, min(100.0, round(score, 1)))
            return parsed

        except Exception as e:
            if attempt < max_retries:
                backoff_time = 1.5 * (attempt + 1)
                print(f"[LLM Evaluator Async] Attempt {attempt + 1} failed: {e}. Retrying in {backoff_time}s...")
                await asyncio.sleep(backoff_time)
            else:
                print(f"[LLM Evaluator Async] Evaluation failed after {max_retries + 1} attempts: {e}")
                return {
                    "resume_score": 60.0,
                    "score_breakdown": {
                        "prerequisites_score": 20.0,
                        "research_alignment_score": 18.0,
                        "technical_skills_score": 12.0,
                        "projects_achievements_score": 10.0
                    },
                    "matching_skills": [],
                    "missing_skills": [],
                    "summary_reasoning": f"Default baseline assigned due to temporary evaluation service unavailability ({str(e)})."
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
            temperature=0.2
        )

        raw_content = response.choices[0].message.content
        cleaned = _clean_json_content(raw_content)
        parsed = json.loads(cleaned)

        score = float(parsed.get("resume_score", 60.0))
        parsed["resume_score"] = max(0.0, min(100.0, round(score, 1)))
        return parsed

    except Exception as e:
        print(f"[LLM Evaluator Sync] OpenRouter Evaluation Error: {e}")
        return {
            "resume_score": 60.0,
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
