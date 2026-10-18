import uuid
from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, JSON, Float, text, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("teacher", "student", name="user_roles"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    teacher_profile = relationship("TeacherProfile", back_populates="user", uselist=False)
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)

class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    teacher_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    department = Column(String(100), nullable=False)

    user = relationship("User", back_populates="teacher_profile")

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    student_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)

    user = relationship("User", back_populates="student_profile")

class AdmissionOpening(Base):
    __tablename__ = "admission_openings"

    opening_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String(36), ForeignKey("teacher_profiles.teacher_id", ondelete="CASCADE"), nullable=False)
    program_type = Column(Enum("MTech", "PhD", name="program_types"), nullable=False)
    title = Column(String(150), nullable=False)
    department = Column(String(100), nullable=False)
    
    # JD / Research Requirements
    description = Column(Text, nullable=True)             # Overview of research lab / project scope
    research_areas = Column(JSON, nullable=True)         # Target research domains e.g., ["NLP", "Computer Vision"]
    preferred_skills = Column(JSON, nullable=True)        # Nice-to-have tools e.g., ["PyTorch", "Docker"]

    # Academic Thresholds & Coursework
    min_gpa = Column(Float, nullable=False, default=6.0)
    min_gate_score = Column(Float, nullable=True)
    prerequisites = Column(JSON, nullable=False)
    syllabus_topics = Column(JSON, nullable=False)
    
    # Opening Date Window
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    teacher = relationship("TeacherProfile")

class Application(Base):
    __tablename__ = "applications"

    application_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("student_profiles.student_id", ondelete="CASCADE"), nullable=False)
    opening_id = Column(String(36), ForeignKey("admission_openings.opening_id", ondelete="CASCADE"), nullable=False)
    gpa = Column(Float, nullable=False)
    gate_score = Column(Float, nullable=True)
    resume_url = Column(String(500), nullable=True)

    # Evaluation Scores & Feedback
    resume_score = Column(Float, nullable=True)
    resume_feedback = Column(JSON, nullable=True)

    status = Column(
        Enum(
            "APPLIED",
            "SHORTLISTED",
            "REJECTED",
            "INTERVIEW_PENDING",
            "ACCEPTED",
            "COMPLETED",
            name="application_status"
        ),
        default="APPLIED",
        nullable=False
    )
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    student = relationship("StudentProfile")
    opening = relationship("AdmissionOpening")