import asyncio
from typing import Optional
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from models import User, StudentProfile, AdmissionOpening, Application
from schemas import EvaluateResumesSchema
from config.settings import MAX_FILE_SIZE
from services.cloudinary_service import upload_resume
from services.pdf_service import extract_text_from_pdf_url, extract_text_from_pdf_url_async, fetch_pdf_bytes
from services.llm_service import evaluate_resume_with_llm, evaluate_resume_with_llm_async
from controllers.opening_controller import compute_opening_status
from utils.security import verify_token_str

def get_opening_applicants(opening_id: str, db: Session, current_user: dict) -> dict:
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can view applicants.")

    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    applications = (
        db.query(Application, User.name, User.email)
        .join(StudentProfile, Application.student_id == StudentProfile.student_id)
        .join(User, StudentProfile.user_id == User.user_id)
        .filter(Application.opening_id == opening_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    result = []
    for app_item, student_name, student_email in applications:
        result.append({
            "application_id": app_item.application_id,
            "student_name": student_name,
            "student_email": student_email,
            "gpa": app_item.gpa,
            "gate_score": app_item.gate_score,
            "resume_url": app_item.resume_url,
            "resume_score": app_item.resume_score,
            "resume_feedback": app_item.resume_feedback,
            "status": app_item.status,
            "applied_at": app_item.created_at.isoformat()
        })

    return {
        "opening": {
            "opening_id": opening.opening_id,
            "title": opening.title,
            "program_type": opening.program_type,
            "min_gpa": opening.min_gpa,
            "min_gate_score": opening.min_gate_score,
            "status": compute_opening_status(opening.start_date, opening.end_date)
        },
        "applicants": result
    }

async def evaluate_and_shortlist_candidates(
    opening_id: str,
    payload: EvaluateResumesSchema,
    db: Session,
    current_user: dict
) -> dict:
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can execute evaluation.")

    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    applications = db.query(Application).filter(Application.opening_id == opening_id).all()
    if not applications:
        raise HTTPException(status_code=400, detail="No applications found for this opening.")

    passed_academic_filter = []

    # STEP 1: Academic Threshold Filter
    for app_item in applications:
        fails_gpa = app_item.gpa < opening.min_gpa
        fails_gate = (
            opening.min_gate_score is not None and 
            (app_item.gate_score is None or app_item.gate_score < opening.min_gate_score)
        )

        if fails_gpa or fails_gate:
            app_item.status = "REJECTED"
            app_item.resume_feedback = {
                "summary_reasoning": f"Did not meet academic thresholds (Required GPA: {opening.min_gpa}, Required GATE: {opening.min_gate_score or 'N/A'})."
            }
        else:
            passed_academic_filter.append(app_item)

    # STEP 2: Resume Evaluation (Concurrent with Semaphore + Cached)
    semaphore = asyncio.Semaphore(5)

    async def evaluate_single_application(app_item: Application):
        # 2a. Check Cache: If already evaluated and not forcing re-evaluation, reuse existing score
        if not payload.force_reevaluate and app_item.resume_score is not None and app_item.resume_feedback is not None:
            return

        async with semaphore:
            if app_item.resume_url:
                resume_text = await extract_text_from_pdf_url_async(app_item.resume_url)
                if resume_text:
                    eval_result = await evaluate_resume_with_llm_async(resume_text, opening)
                    app_item.resume_score = float(eval_result.get("resume_score", 60.0))
                    app_item.resume_feedback = eval_result
                else:
                    gpa_normalized = round((app_item.gpa / 10.0) * 100, 1)
                    app_item.resume_score = min(gpa_normalized, 55.0)
                    app_item.resume_feedback = {
                        "resume_score": app_item.resume_score,
                        "score_breakdown": {
                            "prerequisites_score": 15.0,
                            "research_alignment_score": 15.0,
                            "technical_skills_score": 15.0,
                            "projects_achievements_score": 10.0
                        },
                        "matching_skills": [],
                        "missing_skills": [],
                        "summary_reasoning": "Could not extract readable text from PDF resume. Scored using baseline academic metric."
                    }
            else:
                # For candidates without resume uploads (e.g. M.Tech applications)
                gpa_normalized = round((app_item.gpa / 10.0) * 100, 1)
                app_item.resume_score = gpa_normalized
                app_item.resume_feedback = {
                    "resume_score": gpa_normalized,
                    "score_breakdown": {
                        "prerequisites_score": round((app_item.gpa / 10.0) * 35, 1),
                        "research_alignment_score": round((app_item.gpa / 10.0) * 30, 1),
                        "technical_skills_score": round((app_item.gpa / 10.0) * 20, 1),
                        "projects_achievements_score": round((app_item.gpa / 10.0) * 15, 1)
                    },
                    "matching_skills": [],
                    "missing_skills": [],
                    "summary_reasoning": "Evaluated based on normalized GPA academic performance."
                }

    tasks = [evaluate_single_application(app) for app in passed_academic_filter]
    if tasks:
        await asyncio.gather(*tasks)

    # STEP 3: Capacity Shortlisting
    passed_academic_filter.sort(key=lambda x: x.resume_score or 0.0, reverse=True)

    capacity = payload.positions_available
    shortlisted_count = 0

    for idx, app_item in enumerate(passed_academic_filter):
        if idx < capacity:
            app_item.status = "SHORTLISTED"
            shortlisted_count += 1
        else:
            app_item.status = "REJECTED"

    db.commit()

    return {
        "message": "Evaluation and capacity shortlisting completed successfully.",
        "total_applications": len(applications),
        "passed_academic_filter": len(passed_academic_filter),
        "shortlisted": shortlisted_count,
        "rejected": len(applications) - shortlisted_count
    }

async def apply_for_opening(
    opening_id: str,
    gpa: float,
    gate_score: Optional[float],
    resume: Optional[UploadFile],
    db: Session,
    current_user: dict
) -> dict:
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can apply.")

    user_id = current_user["user_id"]
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Student profile missing.")

    opening = db.query(AdmissionOpening).filter(AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    op_status = compute_opening_status(opening.start_date, opening.end_date)
    if op_status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Cannot apply. Opening window is {op_status.lower()}.")

    existing_app = db.query(Application).filter(
        Application.student_id == student.student_id,
        Application.opening_id == opening_id
    ).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="You have already applied for this opening.")

    if gpa < opening.min_gpa:
        raise HTTPException(status_code=400, detail=f"Your GPA ({gpa}) is below the minimum ({opening.min_gpa}).")

    if opening.min_gate_score and (gate_score is None or gate_score < opening.min_gate_score):
        raise HTTPException(status_code=400, detail=f"Minimum GATE score of {opening.min_gate_score} is required.")

    resume_url = None
    if opening.program_type == "PhD":
        if not resume or not resume.filename:
            raise HTTPException(status_code=400, detail="Applications require a resume (PDF or DOCX) upload.")

    if resume and resume.filename:
        filename_lower = resume.filename.lower()
        allowed_extensions = (".pdf", ".docx")
        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail="Resume must be in PDF or DOCX format.")

        try:
            resume.file.seek(0, 2)
            file_size = resume.file.tell()
            resume.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Resume file size must be less than 5MB.")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file payload.")

        try:
            resume_url = upload_resume(resume.file, student.student_id, opening_id, filename=resume.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")

    new_application = Application(
        student_id=student.student_id,
        opening_id=opening_id,
        gpa=gpa,
        gate_score=gate_score,
        resume_url=resume_url,
        status="APPLIED"
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return {
        "message": "Application submitted successfully", 
        "application_id": new_application.application_id,
        "resume_url": resume_url
    }

def get_student_applications(db: Session, current_user: dict) -> list:
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can view application status.")

    user_id = current_user["user_id"]
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile record not found.")

    user_applications = (
        db.query(Application, AdmissionOpening)
        .join(AdmissionOpening, Application.opening_id == AdmissionOpening.opening_id)
        .filter(Application.student_id == student.student_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    result = []
    for app_item, opening in user_applications:
        result.append({
            "application_id": app_item.application_id,
            "opening_id": opening.opening_id,
            "title": opening.title,
            "program_type": opening.program_type,
            "department": opening.department,
            "gpa": app_item.gpa,
            "gate_score": app_item.gate_score,
            "resume_url": app_item.resume_url,
            "status": app_item.status,
            "resume_score": app_item.resume_score,
            "resume_feedback": app_item.resume_feedback,
            "applied_at": app_item.created_at.isoformat()
        })

    return result

def stream_application_resume(application_id: str, token: Optional[str], db: Session) -> Response:
    """Fetches PDF from Cloudinary using backend credentials and streams inline to browser."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing."
        )

    # Validate JWT passed via query parameter
    _ = verify_token_str(token)

    app_item = db.query(Application).filter(Application.application_id == application_id).first()
    if not app_item or not app_item.resume_url:
        raise HTTPException(status_code=404, detail="Resume file not found for this application.")

    try:
        doc_bytes = fetch_pdf_bytes(app_item.resume_url)
        is_docx = app_item.resume_url.lower().endswith(".docx")
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if is_docx else "application/pdf"
        ext = "docx" if is_docx else "pdf"

        return Response(
            content=doc_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename=resume_{application_id}.{ext}"
            }
        )
    except Exception as e:
        print(f"[Resume View Error] Failed to stream resume: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load resume document.")
