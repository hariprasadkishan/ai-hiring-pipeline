from typing import Optional
from pydantic import BaseModel, EmailStr

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
