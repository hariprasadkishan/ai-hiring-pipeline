import enum
import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, Text, JSON, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from database import Base  # Adjust import based on your setup

class InterviewSessionStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    TERMINATED_ABNORMALLY = "TERMINATED_ABNORMALLY"

class MessageSender(str, enum.Enum):
    AI = "AI"
    CANDIDATE = "CANDIDATE"

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.application_id"), nullable=False, unique=True)
    status = Column(Enum(InterviewSessionStatus), default=InterviewSessionStatus.PENDING, nullable=False)
    
    total_questions = Column(Integer, default=5, nullable=False)
    current_question_index = Column(Integer, default=0, nullable=False)
    
    overall_score = Column(Float, nullable=True)
    evaluation_report = Column(JSON, nullable=True)
    termination_reason = Column(String(100), nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    messages = relationship("InterviewMessage", back_populates="session", cascade="all, delete-orphan")

class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    message_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("interview_sessions.session_id"), nullable=False)
    
    sender = Column(Enum(MessageSender), nullable=False)
    question_num = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    turn_score = Column(Float, nullable=True)
    turn_feedback = Column(JSON, nullable=True)
    telemetry_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("InterviewSession", back_populates="messages")

class InterviewSlot(Base):
    __tablename__ = "interview_slots"

    slot_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opening_id = Column(String(36), ForeignKey("admission_openings.opening_id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    booked_by_application_id = Column(String(36), ForeignKey("applications.application_id", ondelete="SET NULL"), unique=True, nullable=True)
    confirmation_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    application = relationship("Application")
    opening = relationship("AdmissionOpening")
