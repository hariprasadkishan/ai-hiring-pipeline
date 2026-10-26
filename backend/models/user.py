import uuid
from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, text
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
