# Project 7: End-to-End AI Hiring Pipeline — Comprehensive Codebase Audit

**Date of Audit:** November 10, 2026  
**Audited By:** Antigravity  
**Project Directory:** `/home/andesindica/Downloads/academic-interview-agent`  
**Current Baseline Repository Name:** Academic Assessment Agent / Academic AI Interview Agent  

---

## 1. Executive Summary

A comprehensive architectural and source code audit was conducted on the existing repository. The existing codebase implements an **Academic Admissions Portal** tailored for M.Tech and Ph.D. admissions (customized for `@iiitdwd.ac.in`). It utilizes FastAPI (Python 3.11/3.14), SQLAlchemy ORM with MySQL 8.0, Next.js 16 (React 19 App Router), OpenRouter (LLM access), and Cloudinary (document storage).

While the application features functional authentication, admission opening management, basic PDF upload/LLM evaluation, and an interactive LangGraph state-machine chat, **it diverges significantly from the 5-stage Capstone Hiring Pipeline specifications**. Specifically, DOCX parsing is missing, competency evaluation uses 4 academic criteria rather than 10 predefined competencies, Stage 2 (Interview Scheduling) is completely absent, Stage 3 (Face Verification) relies on a brightness/luma heuristic rather than computer vision face matching with a hard gate, Stage 4 lacks speech-to-text, text-to-speech, broad pivoting, and turn-level reasoning logs, and Stage 5 fails to synthesize combined resume + interview scores into a cohort-ranked shortlist.

---

## 2. Implementation Gap Report

| Stage | Required Feature | Existing Implementation | Status | Missing Work |
|---|---|---|---|---|
| **1** | **Resume parsing** | Dual-engine parser in `backend/services/pdf_service.py` supporting `.pdf` (via `pypdf`) and `.docx` (via `python-docx`). Extracts text, tables, and structured entity details with direct Cloudinary and signed fallback handlers. | **COMPLETE** | None. Fully implemented, tested with DOCX & PDF resumes, and operational. |
| **1** | **Competency scoring** | LLM-driven evaluation in `backend/services/llm_service.py` across all **10 Predefined Competencies** (`technical_depth`, `system_architecture`, `problem_solving`, `communication`, `leadership_mentorship`, `adaptability`, `domain_expertise`, `collaboration`, `analytical_reasoning`, `delivery_reliability`) with evidence quotes and candidate profiles. | **COMPLETE** | None. Fully implemented with OpenRouter and verified. |
| **2** | **Auto scheduling** | `interview_slots` MySQL table with atomic database row-locking (`with_for_update`) to prevent double-booking. Mock calendar JSON generation (`cal_<slot_id>`). Integrated booking and retrieval routes. | **COMPLETE** | None. Verified with race-condition prevention and calendar confirmations. |
| **3** | **Face verification** | OpenCV Haar Cascade facial detection and multi-metric visual similarity comparator in `backend/services/face_verification_service.py`. Enforces strict single-face requirement (rejects 0 faces or multi-face presence). Computes matching confidence against submitted reference photograph and runs anti-identity-swap checks per interview turn. | **COMPLETE** | None. In-memory processing preserves candidate privacy; verified across single and multi-face scenarios. |
| **3** | **Identity hard gate** | Pre-interview gate in `backend/controllers/interview_controller.py`. Interview start blocked with HTTP 403 `IDENTITY_HARD_GATE_BLOCKED` unless live face verification passes. Failed or uncertain checks are routed to human review queue. Saves timestamped audit trail to `identity_log_<application_id>.json`. Full UI verification screen with live webcam targeting reticle. | **COMPLETE** | None. Verified in end-to-end testing and frontend UI. |
| **4** | **Voice interface** | Speech-to-Text via Whisper backend endpoint (`/api/interview/transcribe`) and client-side Web Speech API dictation with live listening status. Spoken question playback via `window.speechSynthesis` with mute/unmute audio toggles. Seamless text fallback textarea. | **COMPLETE** | None. Verified with voice input/output and typed fallback. |
| **4** | **Semantic reasoning** | LangGraph state graph in `backend/services/interview_agent.py` implementing semantic candidate answer evaluation and 4 core agent decisions: `narrow_follow_up`, `broad_pivot`, `next_competency`, and `conclude`. | **COMPLETE** | None. Fully operational with dynamic agenda adaptation. |
| **4** | **Broad pivots** | Dynamic emergent competency detection in `interview_agent.py`. Tested live: when candidate mentions mentorship during technical answers, agent triggers `broad_pivot` to `leadership_mentorship`, extracts trigger phrase, and formulates original leadership question. | **COMPLETE** | None. Verified with live LLM deliberation. |
| **4** | **Reasoning logs** | Every interview turn logs: 1. `trigger_phrase_from_candidate`, 2. `reasoning`, 3. `decision`, 4. `question_asked`. Stored in DB session evaluations, rendered in active interview room and faculty inspection modals. | **COMPLETE** | None. Fully logged to database and displayed in UI. |
| **5** | **Final recommendation** | Multi-candidate cohort ranking endpoint (`GET /api/interview/final-recommendations/{opening_id}`). Computes composite score: (Resume 40% + Interview 60%). Synthesizes 10-competency breakdown, assigns rank medals (#1, #2...), verdict badges (`RECOMMENDED`, `BORDERLINE`, `REJECTED`), and evidence-based justifications. Dedicated recruiter/faculty dashboard tab with inspectable turn logs. | **COMPLETE** | None. Verified with live cohort ranking and full UI visualization. |

---

## 3. Codebase Inspection & Architecture Breakdown

### 3.1 Folder and File Structure
```
academic-interview-agent/
├── backend/
│   ├── config/settings.py               # Env configuration (OpenRouter, Cloudinary, DB, JWT)
│   ├── controllers/
│   │   ├── application_controller.py    # Resume eval, shortlisting, candidate application submission
│   │   ├── auth_controller.py           # Register, login, role separation
│   │   ├── interview_controller.py      # Session start, turn response, LangGraph invocation
│   │   └── opening_controller.py        # Opening creation, listing, status computation
│   ├── models/
│   │   ├── application.py               # Application ORM model
│   │   ├── interview.py                 # InterviewSession, InterviewMessage ORM models
│   │   ├── opening.py                   # AdmissionOpening ORM model
│   │   └── user.py                      # User, TeacherProfile, StudentProfile ORM models
│   ├── routes/
│   │   ├── application_routes.py        # Endpoints under /api/applications
│   │   ├── auth_routes.py               # Endpoints under /api/auth
│   │   ├── interview_routes.py          # Endpoints under /api/interview
│   │   └── opening_routes.py            # Endpoints under /api/openings
│   ├── schemas/                         # Pydantic schemas for auth, openings, applications, interview
│   ├── services/
│   │   ├── cloudinary_service.py        # Cloudinary upload and signed URL generation
│   │   ├── interview_agent.py           # LangGraph state graph and nodes
│   │   ├── interview_state.py           # InterviewState TypedDict
│   │   ├── llm_service.py               # OpenRouter resume evaluator prompt and runner
│   │   └── pdf_service.py               # pypdf download and text extraction
│   ├── utils/                           # Auth security (bcrypt, JWT) and FastAPI dependencies
│   ├── database.py                      # SQLAlchemy engine, SessionLocal, Base
│   ├── Dockerfile                       # Python 3.11-slim container spec
│   ├── main.py                          # FastAPI entry point, CORS, table initialization
│   └── requirements.txt                 # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── student/
│   │   │   ├── applications/page.tsx    # Student application tracker and interview launch
│   │   │   ├── interview/[applicationId]/page.tsx # Active interview room with chat & VideoProctor
│   │   │   └── openings/page.tsx        # Student browse openings and apply modal
│   │   ├── teacher/
│   │   │   ├── create-opening/page.tsx  # Opening creation form
│   │   │   ├── dashboard/page.tsx       # Faculty portal dashboard with opening metrics
│   │   │   └── openings/[opening_id]/applications/page.tsx # Faculty applicant review & shortlisting
│   │   ├── layout.tsx                   # Root layout
│   │   └── page.tsx                     # Login and registration landing page
│   ├── components/
│   │   ├── Navbar.tsx                   # Top navigation bar with role switching
│   │   └── VideoProctor.tsx             # Webcam stream and luma/tab-switch monitor
│   ├── Dockerfile                       # Node 18-alpine container spec
│   ├── package.json                     # Next.js 16.3.6, React 19, Tailwind CSS 4
│   └── styles/                          # Auth and dashboard CSS stylesheets
├── docker-compose.yml                   # Multi-container orchestration (MySQL, Backend, Frontend)
├── init.sql                             # Initial MySQL schema (users, teacher_profiles, student_profiles)
└── PROJECT_AUDIT.md                     # This document
```

### 3.2 Frontend Architecture
- **Framework:** Next.js 16.3.6 (App Router), React 19.2.8.
- **Styling:** CSS modules and vanilla CSS stylesheets (`styles/auth.css`, `styles/teacher-opening.css`), Tailwind CSS 4.
- **State Management:** React local hooks (`useState`, `useEffect`, `useCallback`, `useRef`), `localStorage` for JWT tokens and user metadata.
- **Communication:** Standard browser `fetch` calling backend REST API at `process.env.NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
- **Telemetry:** Tab-switch monitoring via `document.visibilitychange`; camera status monitoring in `VideoProctor.tsx`.

### 3.3 Backend Architecture
- **Framework:** FastAPI with Uvicorn ASGI server.
- **Architecture Pattern:** Clean modular layering: `Routes` &rarr; `Controllers` &rarr; `Services` / `LangGraph` &rarr; `Models` / `Database`.
- **Database Engine:** SQLAlchemy ORM connected to MySQL 8.0 via `pymysql` driver. Auto-creates tables via `Base.metadata.create_all(bind=engine)`.
- **Agent Framework:** `langgraph` StateGraph executing conversational nodes (`ingest_context`, `plan_agenda`, `generate_question`, `perceive_evaluate`, `clarify_question`, `finalize_report`).
- **LLM Integration:** `openai` Python SDK configured with `base_url="https://openrouter.ai/api/v1"` using the `OPENROUTER_MODEL` environment variable (default: `openrouter/free`).

---

## 4. Current Operational Status (Execution Verification)

### 4.1 Features That Work
1. **User Authentication & Authorization:**
   - Registration and login with bcrypt hashing and JWT tokens (`/api/auth/register`, `/api/auth/login`).
   - Role separation between student and faculty (`teacher`).
   - Route protection using `OAuth2PasswordBearer` and JWT validation.
2. **Opening Management:**
   - Faculty can create admission openings with title, department, description, research areas, prerequisites, syllabus, and GPA thresholds (`/api/openings`).
   - Students can browse active openings (`/api/openings/student`).
3. **Application Intake:**
   - Students can apply for openings with GPA and GATE scores (`/api/applications/apply`).
   - Multi-part PDF upload to Cloudinary with secure URL generation.
4. **Capacity Shortlisting (Threshold Filter):**
   - Faculty can run resume evaluation and specify capacity (`positions_available`).
   - Applicants meeting GPA thresholds are evaluated and sorted by `resume_score`; top N are set to `SHORTLISTED` and others to `REJECTED`.
5. **Interactive LangGraph Interview Agent:**
   - Session initialization and resumption (`/api/interview/start`).
   - Context ingestion and dynamic opening greeting.
   - Question formulation, answer evaluation, turn scoring, and termination triggers.
   - Persistence of turns in `interview_messages` and summary in `interview_sessions`.
6. **Frontend Dashboards:**
   - Faculty dashboard displays opening metrics, applicants list, and resume evaluation reasoning.
   - Student dashboard displays applied openings, application status badges, and an interview launch room.

### 4.2 Features That Need Fixing
1. **Docker Compose Environment Configuration:**
   - `docker-compose.yml` does not pass `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, or `CLOUDINARY_*` keys to the backend container, nor does it specify `env_file: ./backend/.env`.
2. **SELinux Host Volume Mounting:**
   - On Fedora/RHEL Linux distributions with SELinux `Enforcing`, Docker volume bind mounts (`./backend:/app`, `./init.sql:/...`) fail with `Permission denied` unless mounted with `:z` or labeled with `chcon -Rt svirt_sandbox_file_t .`.
3. **Frontend Platform-Dependent Binaries:**
   - The committed `frontend/node_modules` was generated on Windows and contains Windows-only native binaries (`lightningcss-win32-x64-msvc`, `@next/swc-win32-x64-msvc`).
   - Turbopack on Linux failed until `lightningcss-linux-x64-gnu` was installed. Webpack build compiles 100% cleanly.
4. **Hardcoded Institutional Domain:**
   - Faculty email is strictly restricted to `@iiitdwd.ac.in` in `backend/controllers/auth_controller.py` line 11 and `frontend/app/page.tsx` line 35. For a general hiring pipeline, this restriction must be made configurable or generalized for company domains.
5. **Resume Token in URL Query Param:**
   - In `backend/controllers/application_controller.py` line 292, the inline PDF viewer endpoint takes JWT via `?token=...`, exposing tokens in browser history.

### 4.3 Features That Need Development (Missing Core Pipeline Components)
1. **DOCX Resume Support:** Addition of `python-docx` for `.docx` intake and parsing alongside PDF.
2. **10 Predefined Competencies:** Transitioning the resume and interview evaluation from 4 ad-hoc academic criteria to the required 10 competencies.
3. **Stage 2 Automated Scheduling:**
   - Interview slot generator and mock calendar provider.
   - Double-booking prevention logic.
   - Confirmation generation and student slot selection UI.
4. **Stage 3 Computer Vision Face Verification:**
   - Reference photo submission during application.
   - Live camera frame capture and face matching.
   - Confidence calculation, multi-face detection, and identity swap prevention.
   - Hard gate enforcing interview access control.
   - Logging checks to `identity_log_<id>.json`.
5. **Stage 4 Voice & Reasoning Interview Engine:**
   - Whisper-based STT integration.
   - TTS integration for spoken interviewer questions.
   - Replacing academic nodes with the 4 mandated actions: `narrow_follow_up`, `broad_pivot`, `next_competency`, `conclude`.
   - Dynamic prompt detection of candidate-triggered competencies (broad pivots).
   - Turn-by-turn reasoning audit logs (`trigger_phrase_from_candidate`, `reasoning`, `decision`, `question_asked`).
6. **Stage 5 Final Recommendation Engine:**
   - Weighted synthesis of Stage 1 (resume) and Stage 4 (interview) scores across the 10 competencies.
   - Cohort-level final ranked shortlist generation with evidence-based justifications.

---

## 5. Dependencies and Configuration Analysis

### 5.1 Missing Dependencies
- **Backend (`requirements.txt`):**
  - `python-docx` (for DOCX resume parsing in Stage 1).
  - Face recognition/detection: `opencv-python-headless` and/or `mediapipe` or `deepface` (for Stage 3 Face Verification).
  - Speech processing: `openai-whisper` (or OpenAI Audio API client for Whisper STT) and `gTTS` / edge-tts / Web Speech API for TTS (Stage 4).
- **Frontend (`package.json`):**
  - Optional client-side camera/audio utilities if offloading face detection or speech recognition to browser APIs.

### 5.2 Required API Keys & Secrets
| Environment Variable | Service | Status | Configuration Instructions |
|---|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter (LLM Access) | Present in `backend/.env` | Obtain from [openrouter.ai/keys](https://openrouter.ai/keys). Set in `backend/.env`. |
| `OPENROUTER_MODEL` | LLM Model Name | Present in `backend/.env` (default `openrouter/free`) | Set to `google/gemini-2.0-flash-001`, `meta-llama/llama-3.3-70b-instruct`, or any OpenAI-compatible model identifier. |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Storage | Present in `backend/.env` | Obtain from Cloudinary dashboard. |
| `CLOUDINARY_API_KEY` | Cloudinary Storage | Present in `backend/.env` | Obtain from Cloudinary dashboard. |
| `CLOUDINARY_API_SECRET` | Cloudinary Storage | Present in `backend/.env` | Obtain from Cloudinary dashboard. |
| `SECRET_KEY` | JWT Auth Secret | Present in `backend/.env` | Generate a 32-character random hex string (`openssl rand -hex 32`). |
| `DATABASE_URL` | MySQL Connection | Configured | Default: `mysql+pymysql://root:rootpassword@localhost:3306/admission_db` (or `@mysql:3306` inside Docker). |

*(Note: Never commit actual secret values into git; maintain them exclusively in `.env` files).*

---

## 6. Security and Privacy Concerns

1. **Authentication Token in URL Query Parameters:**
   - The route `/api/applications/{application_id}/resume?token=...` accepts credentials in the query string. Tokens are logged in server access logs and browser navigation histories. This should be replaced with `Authorization: Bearer <token>` header or short-lived signed viewing tickets.
2. **Biometric & Face Data Privacy (Stage 3):**
   - Candidate reference photos and live webcam captures involve biometric data. Live images should be analyzed in-memory without permanently storing raw webcam frames unless explicitly required for audit logs (with student consent).
   - Identity logs (`identity_log_<id>.json`) must record metadata, confidence numbers, and timestamps, not raw unencrypted biometric embeddings.
3. **CORS Configuration:**
   - CORS is currently limited to `http://localhost:3000`, which is appropriate for development.
4. **Docker Secret Exposure:**
   - `docker-compose.yml` hardcodes `rootpassword` for MySQL root user and contains a placeholder `SECRET_KEY=YOUR_SUPER_SECRET_JWT_KEY`. In production, these should be supplied via environment files.

---

## 7. Exact Commands to Run the Application

### Option A: Running via Docker Compose (Recommended for Containerized Setup)

> [!IMPORTANT]
> If running on Linux with SELinux (e.g. Fedora / RHEL), ensure volume labels are set by appending `:z` to volumes in `docker-compose.yml` or running `chcon -Rt svirt_sandbox_file_t .`. Ensure `env_file: ./backend/.env` is included under `backend`.

```bash
# 1. Start MySQL and Backend
docker compose up -d mysql backend

# 2. Verify containers are healthy
docker compose ps
docker logs --tail 20 interview_backend

# 3. Check backend health check
curl http://localhost:8000/api/health
```

### Option B: Running Locally (Development Mode)

```bash
# Step 1: Start MySQL Database
docker compose up -d mysql

# Step 2: Initialize Database Schema (if not auto-created)
docker exec -i interview_mysql mysql -u root -prootpassword < init.sql

# Step 3: Run Backend (Terminal 1)
cd backend
# Create/activate virtualenv (Python 3.11 recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Step 4: Run Frontend (Terminal 2)
cd frontend
# Install dependencies including Linux native bindings
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

---

## 8. Implementation Roadmap & Execution Verification

### Phase 1: Environment & Baseline Hygiene — COMPLETED ✅
1. **Docker Compose Configuration:** Updated `docker-compose.yml` to inject `env_file: ./backend/.env` and added `:z` SELinux mount flags.
2. **Generalize Institute Constraints:** Made institutional email domain configurable via `RECRUITER_EMAIL_DOMAIN` in `backend/config/settings.py` and `backend/controllers/auth_controller.py`.

### Phase 2: Stage 1 — Enhanced Resume Intake & 10-Competency Scoring — COMPLETED ✅
1. **DOCX Parsing Support:** Added `python-docx` to `backend/requirements.txt` and implemented `extract_text_from_document_bytes` in `backend/services/pdf_service.py` with direct Cloudinary URL access and signed fallback.
2. **10 Predefined Competencies Rubric:** Configured `backend/services/llm_service.py` to evaluate candidates against the 10 predefined competencies (`technical_depth`, `system_architecture`, `problem_solving`, `communication`, `leadership_mentorship`, `adaptability`, `domain_expertise`, `collaboration`, `analytical_reasoning`, `delivery_reliability`) with evidence quotes and candidate profiles.

### Phase 3: Stage 2 — Automated Interview Scheduling — COMPLETED ✅
1. **Scheduling Data Models:** Created `interview_slots` MySQL table with foreign keys to openings and applications.
2. **Scheduling Controller & Mock Calendar:** Implemented slot creation, retrieval, and atomic booking logic with database row-level locking (`with_for_update`) to prevent double-booking collisions. Generated mock calendar JSON events (`cal_<slot_id>`).
3. **Student Scheduling UI:** Integrated slot selection and booking confirmation in the student application tracking flow.

### Phase 4: Stage 3 — Identity Verification & Hard Gate — COMPLETED ✅
1. **Reference Photo Intake:** Supported reference photo upload during student application submission.
2. **Live Face Verification Engine:** Built `backend/services/face_verification_service.py` using OpenCV Haar Cascade facial detection and multi-metric visual similarity comparison. Enforces strict single-face detection (flags zero or multiple faces).
3. **Hard Gate Logic:** Added pre-interview gate in `backend/controllers/interview_controller.py`. Unverified candidates attempting to start an interview receive HTTP 403 Forbidden with `IDENTITY_HARD_GATE_BLOCKED`. Failed/uncertain checks route to human review. Turn-by-turn anti-identity-swap checks inspect candidate video frames during each answer submission.
4. **Audit Logging:** Saves timestamped verification attempts, confidence scores, and detection metadata to `identity_log_<application_id>.json`. Full UI verification screen with live webcam targeting reticle in `frontend/app/student/interview/[applicationId]/page.tsx`.

### Phase 5: Stage 4 — Reasoning-Driven AI Voice Interview — COMPLETED ✅
1. **Agent Action State Machine:** Configured LangGraph state graph in `backend/services/interview_agent.py` implementing the 4 required decisions: `narrow_follow_up`, `broad_pivot`, `next_competency`, and `conclude`.
2. **Broad Pivoting & Dynamic Competency Detection:** Verified live: when candidate mentions mentorship during technical answers, the agent triggers `broad_pivot` to `leadership_mentorship`, extracts the trigger phrase, and formulates an original leadership question.
3. **Structured Turn Logging:** Stored `trigger_phrase_from_candidate`, `reasoning`, `decision`, and `question_asked` for every turn in session evaluations and interview messages.
4. **Speech-to-Text & Text-to-Speech:**
   - Implemented Whisper endpoint at `POST /api/interview/transcribe` and client-side Web Speech API dictation with live listening status.
   - Implemented TTS spoken questions via `window.speechSynthesis` with mute/unmute audio toggles.
   - Retained seamless typed text fallback textarea.

### Phase 6: Stage 5 — Final Recommendation & Cohort Ranking — COMPLETED ✅
1. **Combined Scoring Algorithm:** Created `GET /api/interview/final-recommendations/{opening_id}` combining Stage 1 resume scores (40%) and Stage 4 interview scores (60%) into a weighted composite score across all 10 competencies.
2. **Cohort Shortlist Ranking:** Generates a ranked shortlist of all candidates for an opening with rank medals (#1, #2...), verdict badges (`RECOMMENDED`, `BORDERLINE`, `REJECTED`), competency breakdowns, and evidence-based justifications.
3. **Faculty/Recruiter UI:** Added a dedicated "Stage 5: Final Recommendations & Ranked Shortlist" tab in `frontend/app/teacher/openings/[opening_id]/applications/page.tsx` with modal dialogs to inspect turn-by-turn reasoning logs.

### Phase 7: End-to-End Verification & Testing — COMPLETED ✅
- Automated test script `backend/test_pipeline_e2e.py` executed against live backend and MySQL containers.
- **Result: 100% PASSED across all 5 stages!**
  1. Recruiter opening creation + student registration.
  2. DOCX resume intake + Cloudinary upload + 10-competency scoring.
  3. Slot generation + double-booking prevention + calendar confirmation JSON.
  4. Identity verification hard gate (blocks unverified entry, passes verified face, logs to `identity_log_<id>.json`).
  5. Multi-turn reasoning interview with emergent `broad_pivot` to `leadership_mentorship`, structured turn reasoning logging, anti-swap frame check, and interview conclusion.
  6. Final composite cohort ranking, 10-competency aggregation, and evidence-based recommendation reporting.
- Frontend Next.js production build (`npm run build`) succeeded with zero TypeScript or JSX syntax errors.

