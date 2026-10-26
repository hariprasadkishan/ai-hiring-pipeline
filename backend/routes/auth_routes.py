from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas import RegisterSchema, LoginSchema
from controllers.auth_controller import register_user, login_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterSchema, db: Session = Depends(get_db)):
    return register_user(payload, db)

@router.post("/login")
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    return login_user(credentials, db)
