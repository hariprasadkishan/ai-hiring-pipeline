# Backward compatibility shim re-exporting models from models package
from models import (
    User,
    TeacherProfile,
    StudentProfile,
    AdmissionOpening,
    Application,
    InterviewSession,
    InterviewMessage,
    InterviewSessionStatus,
    MessageSender,
    InterviewSlot,
)

__all__ = [
    "User",
    "TeacherProfile",
    "StudentProfile",
    "AdmissionOpening",
    "Application",
    "InterviewSession",
    "InterviewMessage",
    "InterviewSessionStatus",
    "MessageSender",
    "InterviewSlot",
]