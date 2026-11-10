import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# JWT & Auth
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
RECRUITER_EMAIL_DOMAIN = os.getenv("RECRUITER_EMAIL_DOMAIN", "").strip()

# Upload limits
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB Limit

# OpenRouter LLM Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "your_cloud_name")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "your_api_key")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "your_api_secret")

# Database Configuration
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpassword")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL_BASE = os.getenv(
        "DATABASE_URL_BASE", 
        "mysql+pymysql://root:{password}@localhost:3306/admission_db"
    )
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = DATABASE_URL_BASE.format(password=encoded_password)

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
