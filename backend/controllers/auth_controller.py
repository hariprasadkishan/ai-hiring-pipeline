from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models import User, TeacherProfile, StudentProfile
from schemas import RegisterSchema, LoginSchema
from utils.security import hash_password, verify_password, create_access_token

def register_user(payload: RegisterSchema, db: Session) -> dict:
    if payload.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    if payload.role == "teacher" and not payload.email.endswith("@iiitdwd.ac.in"):
        raise HTTPException(
            status_code=400, 
            detail="Faculty registration is restricted to official @iiitdwd.ac.in accounts only."
        )

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if payload.role == "teacher":
        teacher_prof = TeacherProfile(
            user_id=new_user.user_id,
            department=payload.department or "General"
        )
        db.add(teacher_prof)
    else:
        student_prof = StudentProfile(
            user_id=new_user.user_id,
            phone=payload.phone
        )
        db.add(student_prof)

    db.commit()
    return {"message": "User registered successfully"}

def login_user(credentials: LoginSchema, db: Session) -> dict:
    user = db.query(User).filter(User.email == credentials.email).first()

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
