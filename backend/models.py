# Backward compatibility shim re-exporting models from models package
from models import (
    User,
    TeacherProfile,
    StudentProfile,
    AdmissionOpening,
    Application,
)

__all__ = [
    "User",
    "TeacherProfile",
    "StudentProfile",
    "AdmissionOpening",
    "Application",
]