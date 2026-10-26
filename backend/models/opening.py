import uuid
from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, JSON, Float, text, Text
from sqlalchemy.orm import relationship
from database import Base
from models.user import TeacherProfile

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
