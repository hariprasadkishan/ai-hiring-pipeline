import os
import re
import io
import json
import datetime
import httpx
from pypdf import PdfReader
from typing import List, Optional
import jwt
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy.orm import Session
from fastapi.responses import Response
from openai import OpenAI
import cloudinary.utils

from database import engine, Base, get_db
import models

load_dotenv()

# Configuration Constants
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB Limit

# OpenRouter Client Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Cloudinary Setup
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "your_cloud_name"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "your_api_key"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "your_api_secret"),
    secure=True
)

# Passlib & Security Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_data(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise credentials_exception
            
        return {"user_id": user_id, "role": role}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise credentials_exception

# Pydantic Schemas
class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # 'teacher' or 'student'
    department: Optional[str] = None
    phone: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    selected_role: str

class OpeningCreateSchema(BaseModel):
    title: str
    program_type: str  # 'MTech' or 'PhD'
    department: str
    description: Optional[str] = None
    research_areas: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    min_gpa: float = Field(gt=0, le=10.0)
    min_gate_score: Optional[float] = None
    prerequisites: List[str]
    syllabus_topics: List[str]
    start_date: datetime.datetime
    end_date: datetime.datetime

    @model_validator(mode='after')
    def validate_dates(self) -> 'OpeningCreateSchema':
        if self.end_date <= self.start_date:
            raise ValueError('End date must be after start date')
        return self

class EvaluateResumesSchema(BaseModel):
    positions_available: int = Field(gt=0, description="Number of positions faculty wants to fill")

# Status Helper
def compute_opening_status(start_date: datetime.datetime, end_date: datetime.datetime) -> str:
    now = datetime.datetime.now(datetime.timezone.utc) if start_date.tzinfo else datetime.datetime.now()
    if now < start_date:
        return "UPCOMING"
    elif start_date <= now <= end_date:
        return "ACTIVE"
    else:
        return "CLOSED"



def extract_text_from_pdf_url(pdf_url: str) -> str:
    """Generates an authenticated Cloudinary download URL and extracts PDF text."""
    try:
        print(f"[PDF Extractor] Processing URL: {pdf_url}")

        # 1. Determine resource_type (image vs raw)
        resource_type = "raw" if "/raw/upload/" in pdf_url else "image"

        # 2. Extract public_id from Cloudinary URL (stripping /upload/, version numbers, and .pdf suffix)
        match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.pdf)?$', pdf_url, re.IGNORECASE)
        public_id = match.group(1) if match else pdf_url

        print(f"[PDF Extractor] Extracted Public ID: '{public_id}' (Type: '{resource_type}')")

        # 3. Generate a signed API download URL using Cloudinary SDK
        download_url = cloudinary.utils.private_download_url(
            public_id=public_id,
            format="pdf" if resource_type == "image" else None,
            resource_type=resource_type,
            type="upload"
        )
        print(f"[PDF Extractor] Generated signed API URL: {download_url}")

        # 4. Fetch PDF stream directly from Cloudinary API without raw Basic Auth headers
        response = httpx.get(
            download_url,
            timeout=25.0,
            follow_redirects=True
        )
        response.raise_for_status()

        # Verify response starts with %PDF header
        if not response.content.startswith(b"%PDF"):
            print("[PDF Extractor Error] Downloaded payload is not a valid PDF file stream.")
            return ""

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        extracted_text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted_text += page_text + "\n"

        extracted_text = extracted_text.strip()
        print(f"[PDF Extractor] Successfully extracted {len(extracted_text)} characters from {len(reader.pages)} page(s).")
        return extracted_text

    except Exception as e:
        print(f"[PDF Extractor Exception] Failed to extract PDF text: {str(e)}")
        return ""

def evaluate_resume_with_llm(resume_text: str, opening: models.AdmissionOpening) -> dict:
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

# Database Initialization
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Academic Assessment Agent API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Endpoints
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(payload: RegisterSchema, db: Session = Depends(get_db)):
    if payload.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    if payload.role == "teacher" and not payload.email.endswith("@iiitdwd.ac.in"):
        raise HTTPException(
            status_code=400, 
            detail="Faculty registration is restricted to official @iiitdwd.ac.in accounts only."
        )

    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if payload.role == "teacher":
        teacher_prof = models.TeacherProfile(
            user_id=new_user.user_id,
            department=payload.department or "General"
        )
        db.add(teacher_prof)
    else:
        student_prof = models.StudentProfile(
            user_id=new_user.user_id,
            phone=payload.phone
        )
        db.add(student_prof)

    db.commit()
    return {"message": "User registered successfully"}

@app.post("/api/auth/login", tags=["Authentication"])
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if user.role != credentials.selected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account is registered as a {user.role}. Please select the correct tab."
        )

    token = create_access_token({
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        "name": user.name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "user_id": user.user_id
    }

# Faculty Endpoints
@app.post("/api/openings", status_code=status.HTTP_201_CREATED, tags=["Admission Openings"])
def create_opening(
    payload: OpeningCreateSchema, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data) 
):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can post openings.")

    user_id = current_user["user_id"]
    teacher = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=403, detail="Faculty profile metadata missing")

    new_opening = models.AdmissionOpening(
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

@app.get("/api/openings/teacher", tags=["Admission Openings"])
def get_teacher_openings(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can view this dashboard.")

    user_id = current_user["user_id"]
    teacher = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Faculty profile record not found.")

    openings = (
        db.query(models.AdmissionOpening)
        .filter(models.AdmissionOpening.teacher_id == teacher.teacher_id)
        .order_by(models.AdmissionOpening.created_at.desc())
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

@app.get("/api/openings/{opening_id}/applicants", tags=["Faculty Evaluation"])
def get_opening_applicants(
    opening_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can view applicants.")

    opening = db.query(models.AdmissionOpening).filter(models.AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    applications = (
        db.query(models.Application, models.User.name, models.User.email)
        .join(models.StudentProfile, models.Application.student_id == models.StudentProfile.student_id)
        .join(models.User, models.StudentProfile.user_id == models.User.user_id)
        .filter(models.Application.opening_id == opening_id)
        .order_by(models.Application.created_at.desc())
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

@app.post("/api/openings/{opening_id}/evaluate-resumes", tags=["Faculty Evaluation"])
def evaluate_and_shortlist_candidates(
    opening_id: str,
    payload: EvaluateResumesSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Access denied. Only faculty can execute evaluation.")

    opening = db.query(models.AdmissionOpening).filter(models.AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    applications = db.query(models.Application).filter(models.Application.opening_id == opening_id).all()
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

    # STEP 2: Resume Evaluation via OpenRouter
    for app_item in passed_academic_filter:
        if app_item.resume_url:
            resume_text = extract_text_from_pdf_url(app_item.resume_url)
            if resume_text:
                eval_result = evaluate_resume_with_llm(resume_text, opening)
                app_item.resume_score = float(eval_result.get("resume_score", 70.0))
                app_item.resume_feedback = eval_result
            else:
                app_item.resume_score = 50.0
                app_item.resume_feedback = {"summary_reasoning": "Could not extract readable text from PDF resume."}
        else:
            gpa_normalized = (app_item.gpa / 10.0) * 100
            app_item.resume_score = round(gpa_normalized, 1)
            app_item.resume_feedback = {"summary_reasoning": "Evaluated based on normalized GPA performance."}

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

# Student Endpoints
@app.get("/api/openings/student", tags=["Student Openings"])
def get_student_openings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can view these openings.")

    user_id = current_user["user_id"]
    student = db.query(models.StudentProfile).filter(models.StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Student profile missing.")

    openings = db.query(models.AdmissionOpening).order_by(models.AdmissionOpening.created_at.desc()).all()

    applied_opening_ids = set(
        app_item.opening_id
        for app_item in db.query(models.Application.opening_id).filter(models.Application.student_id == student.student_id).all()
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

@app.post("/api/applications/apply", status_code=status.HTTP_201_CREATED, tags=["Student Applications"])
async def apply_for_opening(
    opening_id: str = Form(...),
    gpa: float = Form(...),
    gate_score: Optional[float] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can apply.")

    user_id = current_user["user_id"]
    student = db.query(models.StudentProfile).filter(models.StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Student profile missing.")

    opening = db.query(models.AdmissionOpening).filter(models.AdmissionOpening.opening_id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Opening not found.")

    op_status = compute_opening_status(opening.start_date, opening.end_date)
    if op_status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Cannot apply. Opening window is {op_status.lower()}.")

    existing_app = db.query(models.Application).filter(
        models.Application.student_id == student.student_id,
        models.Application.opening_id == opening_id
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
            raise HTTPException(status_code=400, detail="Ph.D. applications require a resume PDF upload.")

    if resume and resume.filename:
        if resume.content_type != "application/pdf" or not resume.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Resume must be in a valid PDF format.")

        try:
            resume.file.seek(0, 2)
            file_size = resume.file.tell()
            resume.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Resume file size must be less than 5MB.")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file payload.")

        try:
            upload_result = cloudinary.uploader.upload(
                resume.file,
                resource_type="image",
                folder="phd_resumes",
                public_id=f"resume_{student.student_id}_{opening_id}"
            )
            resume_url = upload_result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")

    new_application = models.Application(
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

@app.get("/api/applications/student/my-applications", tags=["Student Applications"])
def get_student_applications(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_data)
):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied. Only students can view application status.")

    user_id = current_user["user_id"]
    student = db.query(models.StudentProfile).filter(models.StudentProfile.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile record not found.")

    user_applications = (
        db.query(models.Application, models.AdmissionOpening)
        .join(models.AdmissionOpening, models.Application.opening_id == models.AdmissionOpening.opening_id)
        .filter(models.Application.student_id == student.student_id)
        .order_by(models.Application.created_at.desc())
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
# --- Token Helper ---
def verify_token_str(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
        return {"user_id": user_id, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise credentials_exception

def get_current_user_data(token: str = Depends(oauth2_scheme)) -> dict:
    return verify_token_str(token)





# --- Resume Streaming Endpoint ---
@app.get("/api/applications/{application_id}/resume", tags=["Faculty Evaluation"])
def stream_application_resume(
    application_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Fetches PDF from Cloudinary using backend credentials and streams inline to browser."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing."
        )

    # Validate JWT passed via query parameter
    current_user = verify_token_str(token)

    app_item = db.query(models.Application).filter(models.Application.application_id == application_id).first()
    if not app_item or not app_item.resume_url:
        raise HTTPException(status_code=404, detail="Resume PDF not found for this application.")

    pdf_url = app_item.resume_url

    try:
        # Determine resource type and extract public_id
        resource_type = "raw" if "/raw/upload/" in pdf_url else "image"
        match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.pdf)?$', pdf_url, re.IGNORECASE)
        public_id = match.group(1) if match else pdf_url

        # Generate signed Cloudinary URL
        download_url = cloudinary.utils.private_download_url(
            public_id=public_id,
            format="pdf" if resource_type == "image" else None,
            resource_type=resource_type,
            type="upload"
        )

        # Download raw bytes on backend
        response = httpx.get(download_url, timeout=25.0, follow_redirects=True)
        response.raise_for_status()

        # Stream directly to browser for inline PDF viewing
        return Response(
            content=response.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=resume_{application_id}.pdf"
            }
        )

    except Exception as e:
        print(f"[Resume View Error] Failed to stream resume: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load resume PDF.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)