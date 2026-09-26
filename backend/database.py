import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpassword")
DATABASE_URL_BASE = os.getenv(
    "DATABASE_URL_BASE", 
    "mysql+pymysql://root:{password}@localhost:3306/admission_db"
)

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = DATABASE_URL_BASE.format(password=encoded_password)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()