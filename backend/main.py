import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # Ensures all ORM models are registered with Base metadata
from config.settings import CORS_ORIGINS
from routes import auth_router, opening_router, application_router, interview_router

# Initialize database schema tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Academic Assessment Agent API",
    version="1.0.0"
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Modular Routers
app.include_router(auth_router)
app.include_router(opening_router)
app.include_router(application_router)
app.include_router(interview_router)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "academic-interview-agent",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)