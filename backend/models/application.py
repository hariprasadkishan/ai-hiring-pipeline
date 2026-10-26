import uuid
from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, JSON, Float, text
from sqlalchemy.orm import relationship
from database import Base
from models.user import StudentProfile
from models.opening import AdmissionOpening

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
