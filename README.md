# Project 7: End-to-End AI Hiring Pipeline

[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)](https://www.mysql.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-SFace%20%26%20YuNet-5C3EE8?logo=opencv)](https://opencv.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange)](https://langchain-ai.github.io/langgraph/)

An autonomous, multi-modal **AI Hiring Pipeline and Technical Interview Platform** that evaluates candidates across five comprehensive stages—from initial resume intake to live biometric identity gating, adaptive reasoning-driven voice interviews, and cohort ranking.

---

## 🌟 Key Features Across the 5 Pipeline Stages

### Stage 1: Resume Intake & 10 Predefined Competencies Scoring
- **Dual-Engine Document Parser:** Parses both `.docx` (via `python-docx`) and `.pdf` (via `pypdf`) with structured entity, table, and text extraction.
- **10 Predefined Competencies Rubric:** Evaluates candidates across 10 specific competencies (`technical_depth`, `system_architecture`, `problem_solving`, `communication`, `leadership_mentorship`, `adaptability`, `domain_expertise`, `collaboration`, `analytical_reasoning`, `delivery_reliability`) with direct quote citations and analyses.
- **Threshold Shortlisting:** Automates initial screening based on GPA, GATE, and rubric thresholds.

### Stage 2: Automated Interview Scheduling & Collision Prevention
- **Slot Reservation Engine:** Database row-locking (`with_for_update`) ensures atomic slot booking, completely eliminating double-booking collisions under concurrent applicant load.
- **Mock Calendar Confirmation:** Generates RFC-compliant calendar confirmation JSON (`cal_<slot_id>`) with meeting links, attendee roles, and ISO timestamps.

### Stage 3: Biometric Identity Verification (Mandatory HARD GATE)
- **Genuine Deep Face Recognition:** Combines **YuNet** (deep face detection & 5-point landmark alignment) with **SFace** (128-dimensional deep face embedding extraction and cosine similarity verification).
- **Strict Single-Face Gate:** Rejects frames with zero faces (obscured/dark camera) or multiple faces (integrity violation).
- **Hard Gate Enforcement:** Unverified candidates attempting to enter an interview receive HTTP `403 Forbidden` (`IDENTITY_HARD_GATE_BLOCKED`).
- **Anti-Swap Monitoring:** Inspects candidate live video telemetry during each answer submission.
- **Audit Logging:** Saves all timestamped verification checks to `identity_log_<application_id>.json`.

### Stage 4: Reasoning-Driven AI Voice Interview
- **Voice Interface:** Speech-to-Text via Whisper backend endpoint (`POST /api/interview/transcribe`) and client-side Web Speech API dictation; Text-to-Speech spoken questions via `window.speechSynthesis` with mute/unmute audio toggles; seamless typed textarea fallback.
- **LangGraph Reasoning State Machine:** Implements four distinct agent decisions:
  1. `narrow_follow_up`: Probes specific technical claims and mechanisms.
  2. `broad_pivot`: Dynamically detects emergent competencies (e.g. mentorship claims trigger an immediate pivot to `leadership_mentorship`).
  3. `next_competency`: Advances to the next planned topic on the evaluation agenda.
  4. `conclude`: Concludes the interview and synthesizes final reports.
- **Turn Reasoning Logs:** Records `trigger_phrase_from_candidate`, `reasoning`, `decision`, and `question_asked` for every turn.

### Stage 5: Final Recommendation & Cohort Ranking
- **Calibrated Composite Scoring:**
  $$\text{Composite Score} = (\text{Resume Score} \times 0.40) + (\text{Interview Score} \times 0.60)$$
- **Cohort Shortlist Ranking:** Ranks all candidates for an opening descending (#1, #2, #3...) with verdict badges (`RECOMMENDED`, `BORDERLINE`, `REJECTED`) and evidence rationales.
- **Recruiter Inspection Modal:** Interactive turn log inspector allowing faculty to review the AI agent's reasoning process behind every interview turn.

---

## 🛠️ Technology Stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Web Speech API.
- **Backend:** FastAPI, Python 3.11/3.14, SQLAlchemy ORM, Uvicorn.
- **Database:** MySQL 8.0 (InnoDB with row-level transaction locks).
- **AI & Reasoning:** LangGraph, OpenRouter (Gemini 2.0 Flash / LLaMA 3.3).
- **Computer Vision:** OpenCV DNN with YuNet (`face_detection_yunet_2023mar.onnx`) and SFace (`face_recognition_sface_2021dec.onnx`).
- **Document & Asset Storage:** Cloudinary raw and image asset management.

---

## 🚀 Quick Start Guide

### 1. Clone & Configure Environment
```bash
git clone <repository_url>
cd academic-interview-agent

# Create backend .env (see .env.example)
cp .env.example backend/.env
# Edit backend/.env to configure OPENROUTER_API_KEY and CLOUDINARY credentials

# Create frontend .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
```

### 2. Start Services via Docker Compose
```bash
# Start MySQL and Backend
docker compose up -d mysql backend

# Verify backend health
curl http://localhost:8000/api/health
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run build
npm run start
```
- **Frontend Portal:** [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Automated Tests

Run the complete 5-stage automated regression test suite:
```bash
docker exec -i interview_backend python3 -u test_pipeline_e2e.py
```

Test Deep Face Verification Unit Tests (Same person, different person, zero face, multi-face):
```bash
docker exec -i interview_backend python3 -c "
import cv2
from services.face_verification_service import perform_identity_verification

img1 = cv2.imread('/app/assets/sample_reference_face.jpg')
img2 = cv2.imread('/app/assets/sample_face_different.jpg')

b1 = cv2.imencode('.jpg', img1)[1].tobytes()
b2 = cv2.imencode('.jpg', img2)[1].tobytes()

print('Same person match:', perform_identity_verification(b1, b1, 'demo')['status'])
print('Different person match:', perform_identity_verification(b2, b1, 'demo')['status'])
"
```

---

## 📚 Project Documentation

- [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) — Comprehensive test report with all 23 test cases, pass/fail status, edge case evaluations, and live outputs.
- [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) — Architectural specifications, Mermaid tier diagrams, LangGraph state machine, and biometric vision pipeline.
- [SETUP_GUIDE.md](SETUP_GUIDE.md) — Detailed setup, asset downloads, Docker deployment, and troubleshooting.
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — Step-by-step 10–12 minute live defense presentation guide.
- [PROJECT_AUDIT.md](PROJECT_AUDIT.md) — Complete codebase audit and execution verification report.
- [MANUAL_TEST_REPORT.md](MANUAL_TEST_REPORT.md) — Step-by-step manual test guide and credential matrix.
- [FIX_REPORT.md](FIX_REPORT.md) — Detailed summary of all system fixes and stability enhancements.

