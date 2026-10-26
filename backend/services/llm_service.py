import json
from openai import OpenAI
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
from models.opening import AdmissionOpening

llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def evaluate_resume_with_llm(resume_text: str, opening: AdmissionOpening) -> dict:
    """
    Evaluates candidate resume text against Opening JD criteria via OpenRouter AI.
    """
    prompt = f"""
    You are an expert academic admissions evaluator.
    Evaluate the candidate's resume against the opening criteria.

    Opening Title: {opening.title} ({opening.program_type})
    Department: {opening.department}
    Project Scope / Description: {opening.description or 'N/A'}
    Target Research Areas: {', '.join(opening.research_areas or [])}
    Preferred Skills: {', '.join(opening.preferred_skills or [])}
    Prerequisites: {', '.join(opening.prerequisites or [])}
    Syllabus Topics: {', '.join(opening.syllabus_topics or [])}

    Candidate Resume Content:
    {resume_text[:4000]}

    Evaluate technical fit and return ONLY valid JSON with this exact structure:
    {{
      "resume_score": <number between 0.0 and 100.0>,
      "matching_skills": [<list of matched skills/domains>],
      "missing_skills": [<list of missing prerequisites/skills>],
      "summary_reasoning": "<2-3 sentence concise assessment>"
    }}
    """

    try:
        response = llm_client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise academic resume evaluator. Always respond in valid raw JSON format without markdown formatting or code blocks."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        
        # Strip markdown ```json backticks if returned by free models
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as e:
        print(f"OpenRouter Evaluation Error: {e}")
        return {
            "resume_score": 50.0,
            "matching_skills": [],
            "missing_skills": [],
            "summary_reasoning": f"Evaluated with default criteria (LLM status: {str(e)})"
        }
