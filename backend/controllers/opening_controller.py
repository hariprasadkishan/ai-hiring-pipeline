import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import TeacherProfile, StudentProfile, AdmissionOpening, Application
from schemas import OpeningCreateSchema

def compute_opening_status(start_date: datetime.datetime, end_date: datetime.datetime) -> str:
    now = datetime.datetime.now(datetime.timezone.utc) if start_date.tzinfo else datetime.datetime.now()
    if now < start_date:
        return "UPCOMING"
    elif start_date <= now <= end_date:
        return "ACTIVE"
    else:
        return "CLOSED"

def create_opening(payload: OpeningCreateSchema, db: Session, current_user: dict) -> dict:
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can post openings.")

    user_id = current_user["user_id"]
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=403, detail="Faculty profile metadata missing")

    new_opening = AdmissionOpening(
        teacher_id=teacher.teacher_id,
        title=payload.title,
        program_type=payload.program_type,
        department=payload.department,
        description=payload.description,
        research_areas=payload.research_areas,
        preferred_skills=payload.preferred_skills,
        min_gpa=payload.min_gpa,
        min_gate_score=payload.min_gate_score,
        prerequisites=payload.prerequisites,
        syllabus_topics=payload.syllabus_topics,
        start_date=payload.start_date,
        end_date=payload.end_date
    )
    db.add(new_opening)
    db.commit()
    db.refresh(new_opening)
    return {"message": "Opening created successfully", "opening_id": new_opening.opening_id}

def get_teacher_openings(db: Session, current_user: dict) -> list:
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can view this dashboard.")

    user_id = current_user["user_id"]
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Faculty profile record not found.")

    openings = (
        db.query(AdmissionOpening)
        .filter(AdmissionOpening.teacher_id == teacher.teacher_id)
        .order_by(AdmissionOpening.created_at.desc())
        .all()
    )

    result = []
    for op in openings:
        result.append({
            "opening_id": op.opening_id,
            "title": op.title,
            "program_type": op.program_type,
            "department": op.department,
            "description": op.description,
            "research_areas": op.research_areas or [],
            "preferred_skills": op.preferred_skills or [],
            "min_gpa": op.min_gpa,
            "min_gate_score": op.min_gate_score,
            "prerequisites": op.prerequisites or [],
            "syllabus_topics": op.syllabus_topics or [],
            "start_date": op.start_date.isoformat(),
            "end_date": op.end_date.isoformat(),
            "status": compute_opening_status(op.start_date, op.end_date)
        })

    return result

def get_student_openings(db: Session, current_user: dict) -> list:
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can view these openings.")

    user_id = current_user["user_id"]
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Student profile missing.")

    openings = db.query(AdmissionOpening).order_by(AdmissionOpening.created_at.desc()).all()

    applied_opening_ids = set(
        app_item.opening_id
        for app_item in db.query(Application.opening_id).filter(Application.student_id == student.student_id).all()
    )

    result = []
    for op in openings:
        op_status = compute_opening_status(op.start_date, op.end_date)
        result.append({
            "opening_id": op.opening_id,
            "title": op.title,
            "program_type": op.program_type,
            "department": op.department,
            "description": op.description,
            "research_areas": op.research_areas or [],
            "preferred_skills": op.preferred_skills or [],
            "min_gpa": op.min_gpa,
            "min_gate_score": op.min_gate_score,
            "prerequisites": op.prerequisites or [],
            "syllabus_topics": op.syllabus_topics or [],
            "start_date": op.start_date.isoformat(),
            "end_date": op.end_date.isoformat(),
            "status": op_status,
            "has_applied": op.opening_id in applied_opening_ids
        })

    return result
