import os
import datetime
from typing import List, Optional
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
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

# Opening Endpoints
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
        raise HTTPException(status_code=403, detail="Access denied.")

    user_id = current_user["user_id"]
    teacher = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=403, detail="Access denied")

    openings = db.query(models.AdmissionOpening).filter(models.AdmissionOpening.teacher_id == teacher.teacher_id).all()
    
    result = []
    for op in openings:
        result.append({
            "opening_id": op.opening_id,
            "title": op.title,
            "program_type": op.program_type,
            "department": op.department,
            "min_gpa": op.min_gpa,
            "min_gate_score": op.min_gate_score,
            "start_date": op.start_date.isoformat(),
            "end_date": op.end_date.isoformat(),
            "status": compute_opening_status(op.start_date, op.end_date)
        })
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)