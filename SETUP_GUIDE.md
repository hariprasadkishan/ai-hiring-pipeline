# Project 7: End-to-End AI Hiring Pipeline — Setup & Installation Guide

This guide provides instructions to set up, configure, and run the complete AI Hiring Pipeline application.

---

## 1. System Prerequisites

Ensure the following tools are installed on your workstation:
- **Docker & Docker Compose** (Docker 24.0+ recommended)
- **Node.js** (v18.x or v20.x+) and **npm**
- **Python** (3.11.x or 3.12.x) *(if running backend outside Docker)*
- **Git**

---

## 2. Environment Variables Configuration

### A. Backend Configuration (`backend/.env`)
Create a file at `backend/.env` with the following parameters:

```env
# Database Credentials
DATABASE_URL=mysql+pymysql://root:rootpassword@mysql:3306/admission_db
# (If running backend directly on host machine, use localhost:3306 instead of mysql:3306)

# JWT Authentication
SECRET_KEY=YOUR_SECURE_RANDOM_SECRET_KEY_MINIMUM_32_CHARACTERS
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Institutional / Enterprise Recruiter Domain
RECRUITER_EMAIL_DOMAIN=iiitdwd.ac.in

# OpenRouter LLM Access
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openrouter/free
# (Recommended production models: google/gemini-2.0-flash-001 or meta-llama/llama-3.3-70b-instruct)

# Cloudinary Storage (Resume Documents)
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

### B. Frontend Configuration (`frontend/.env.local`)
Create a file at `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 3. Deep Learning Model Assets

The computer vision subsystem requires the YuNet detector and SFace recognizer ONNX models in `backend/assets/`. They are downloaded automatically or can be fetched via:

```bash
mkdir -p backend/assets
# Download SFace MobileFaceNet Model (36.9 MB)
curl -L -o backend/assets/face_recognition_sface_2021dec.onnx \
  https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx

# Download YuNet Landmark Detection Model (228 KB)
curl -L -o backend/assets/face_detection_yunet_2023mar.onnx \
  https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
```

---

## 4. Starting the Application

### Option A: Standard Setup (Backend + MySQL in Docker, Frontend on Host) [RECOMMENDED]

1. **Start Database and Backend:**
   ```bash
   # From the project root:
   docker compose up -d mysql backend
   ```

2. **Verify Backend Health:**
   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status":"ok","service":"academic-interview-agent",...}
   ```

3. **Install & Run Frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   npm run start   # Runs on http://localhost:3000
   ```

### Option B: Full Containerized Setup (All services in Docker)

```bash
docker compose up -d
```
All services will start up:
- MySQL: `localhost:3306`
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`

---

## 5. Verification & Testing

Verify that all five stages are operating end-to-end:

```bash
# Execute the full automated regression test suite:
docker exec -i interview_backend python3 -u test_pipeline_e2e.py
```

---

## 6. Troubleshooting Common Issues

1. **SELinux Permission Denied (Fedora / RHEL / CentOS):**
   If Docker fails to bind mount volumes, ensure volume mount flags `:z` are set in `docker-compose.yml` or run:
   ```bash
   chcon -Rt svirt_sandbox_file_t .
   ```

2. **OpenRouter Rate Limits (429 Too Many Requests):**
   If using `openrouter/free`, free-tier rate limits may occasionally trigger. The system includes built-in exponential backoff and deterministic fallbacks to preserve interview continuity. For dedicated evaluations, provide an authenticated OpenRouter API key with paid credits.

3. **Microphone Permissions in Browser:**
   The Web Speech API requires explicit browser microphone permission. When prompted at `http://localhost:3000`, click **"Allow"**. If running in an insecure context (non-localhost HTTP), browsers disable speech recognition — always access via `http://localhost:3000`. If microphone access is denied, use the built-in typed fallback textarea.

