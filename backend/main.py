import os
import datetime
import cloudinary
import cloudinary.uploader
from typing import List, Optional
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models

load_dotenv()

# Configuration Constants
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB Limit

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

# Pydantic Validation Schemas
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

# Status Helper
def compute_opening_status(start_date: datetime.datetime, end_date: datetime.datetime) -> str:
    now = datetime.datetime.now(datetime.timezone.utc) if start_date.tzinfo else datetime.datetime.now()
    if now < start_date:
        return "UPCOMING"
    elif start_date <= now <= end_date:
        return "ACTIVE"
    else:
        return "CLOSED"

# Database & Application Initialization
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

# Admission Opening Endpoints (Faculty)
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied. Only faculty can view this dashboard."
        )

    user_id = current_user["user_id"]
    teacher = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Faculty profile record not found."
        )

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

    # Check opening status window
    op_status = compute_opening_status(opening.start_date, opening.end_date)
    if op_status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Cannot apply. Opening window is {op_status.lower()}.")

    # Prevent duplicate application
    existing_app = db.query(models.Application).filter(
        models.Application.student_id == student.student_id,
        models.Application.opening_id == opening_id
    ).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="You have already applied for this opening.")

    # Validate academic thresholds
    if gpa < opening.min_gpa:
        raise HTTPException(status_code=400, detail=f"Your GPA ({gpa}) is below the minimum ({opening.min_gpa}).")

    if opening.min_gate_score and (gate_score is None or gate_score < opening.min_gate_score):
        raise HTTPException(status_code=400, detail=f"Minimum GATE score of {opening.min_gate_score} is required.")

    # Conditional Resume Validation for Ph.D.
    resume_url = None
    if opening.program_type == "PhD":
        if not resume or not resume.filename:
            raise HTTPException(status_code=400, detail="Ph.D. applications require a resume PDF upload.")

    # Upload PDF file to Cloudinary if provided
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

    # Save Application
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)