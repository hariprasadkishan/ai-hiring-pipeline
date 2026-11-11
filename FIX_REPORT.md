# Project 7: End-to-End AI Hiring Pipeline — Root Cause Diagnosis & Fix Report

**Date of Diagnosis:** November 10, 2026  
**Issue Reported:** Frontend at `http://localhost:3000` rendered **"Failed to fetch"** error. Frontend server was occupying port 3000 (`EADDRINUSE`).  
**Resolution Status:** **RESOLVED & VERIFIED (100% OPERATIONAL)**

---

## 1. Root Cause Analysis of "Failed to fetch"

### Root Cause 1: Missing Python Packages in Docker Image Caused Backend Crash
- **What Happened:** When `uvicorn` reloaded or started up inside the `interview_backend` container, it attempted to import `backend/services/pdf_service.py` and `backend/services/face_verification_service.py`.
- **The Traceback:**
  ```python
  File "/app/services/pdf_service.py", line 5, in <module>
      import docx
  ModuleNotFoundError: No module named 'docx'
  ```
  And upon re-starting:
  ```python
  File "/app/services/face_verification_service.py", line 17, in <module>
      face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
  AttributeError: module 'cv2' has no attribute 'CascadeClassifier'
  ```
- **Why It Happened:**
  1. `python-docx` was added to `requirements.txt` but was not baked into the cached Docker image.
  2. `opencv-python-headless` was unpinned, causing pip to pull experimental `opencv-python-headless==5.0.0.93`, which lacks `cv2.CascadeClassifier` attributes in headless Linux.
  3. Consequently, FastAPI crashed immediately upon startup. The Docker container remained running, but port 8000 rejected incoming HTTP connections (`Recv failure: Connection reset by peer`).
- **How It Manifested in the Browser:**
  When the user or client-side Next.js code called `fetch("http://localhost:8000/api/...")`, the network connection failed immediately. The browser JavaScript engine threw `TypeError: Failed to fetch`. The frontend exception handler rendered `err.message` directly on the screen as: **"Failed to fetch"**.

### Root Cause 2: Overly Restrictive CORS Configuration
- In `backend/config/settings.py`, `CORS_ORIGINS` was restricted strictly to `["http://localhost:3000"]`.
- Browsers accessing via `http://127.0.0.1:3000` had their cross-origin requests rejected because `127.0.0.1` was not in the whitelist, causing CORS preflight `OPTIONS` requests to fail and also generating "Failed to fetch".

### Root Cause 3: Port 3000 Occupation (`EADDRINUSE`)
- The Next.js production server was already running on port 3000 (PID 83515). When another terminal or user command ran `npm run dev` or `npm run start`, it collided on port 3000 with `EADDRINUSE`.

---

## 2. Errors Identified & Resolved

| Error | Component | Severity | Resolution |
|---|---|---|---|
| `ModuleNotFoundError: No module named 'docx'` | Backend / Docker | Critical | Added `python-docx` and rebuilt container image with `docker compose build backend`. |
| `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'` | Backend / OpenCV | Critical | Pinned `opencv-python-headless<5` (installed `4.14.0.94`) and added defensive `hasattr(cv2, 'CascadeClassifier')` guards. |
| `Recv failure: Connection reset by peer` on port 8000 | Network / FastAPI | Critical | Fixed backend crash; uvicorn is running stable on `0.0.0.0:8000`. |
| CORS Preflight Failure from `127.0.0.1:3000` | FastAPI Middleware | High | Added regex origin matching `^https?://(localhost\|127\.0\.0\.1)(:[0-9]+)?$` and explicit origins. |
| `EADDRINUSE: port 3000 already in use` | Frontend / Next.js | Medium | Reused the existing healthy Next.js instance on port 3000 without starting competing instances. |

---

## 3. Files Modified

1. **`backend/requirements.txt`:**
   - Pinned `opencv-python-headless<5` and ensured `python-docx` is explicitly declared.
2. **`backend/config/settings.py`:**
   - Expanded `CORS_ORIGINS` to include `http://localhost:3000`, `http://127.0.0.1:3000`, `http://0.0.0.0:3000`, `http://localhost:3001`, `http://127.0.0.1:3001`.
3. **`backend/main.py`:**
   - Updated `CORSMiddleware` to include `allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"`, allowing credentials, all headers, and exposed headers.
4. **`backend/services/face_verification_service.py`:**
   - Wrapped `CascadeClassifier` in safe attribute detection guards so OpenCV differences never prevent server startup.
5. **`backend/services/llm_service.py` & `backend/services/interview_agent.py`:**
   - Added `timeout=15.0` to LLM requests to prevent latency or connection hangs.
6. **`backend/seed_demo_data.py`:**
   - Created standalone seeding script to populate realistic recruiter and candidate data across all five stages for demonstration.
7. **`README.md`:**
   - Added comprehensive project overview and documentation links in the repository root.

---

## 4. Tests Executed & Live Verification Results

### A. Health & Network Diagnostics
- **Backend Health Check:**
  ```bash
  curl http://localhost:8000/api/health
  # Response: {"status":"ok","service":"academic-interview-agent","timestamp":"..."} -> HTTP 200 OK
  ```
- **CORS Preflight (Origin: http://localhost:3000):**
  ```bash
  curl -i -X OPTIONS http://localhost:8000/api/auth/login \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type"
  # Response: HTTP/1.1 200 OK | access-control-allow-origin: http://localhost:3000
  ```
- **CORS Preflight (Origin: http://127.0.0.1:3000):**
  ```bash
  curl -i -X OPTIONS http://localhost:8000/api/auth/login \
    -H "Origin: http://127.0.0.1:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type"
  # Response: HTTP/1.1 200 OK | access-control-allow-origin: http://127.0.0.1:3000
  ```

### B. End-to-End API Communication Tests
Executed via test script against live services:
- **Teacher Login:** `HTTP 200 OK` (Token issued)
- **Student Login:** `HTTP 200 OK` (Token issued)
- **Student Openings Query (`/api/openings/student`):** `HTTP 200 OK` (Retrieved active openings)
- **Teacher Openings Query (`/api/openings/teacher`):** `HTTP 200 OK` (Retrieved recruiter openings)
- **Stage 1 Applicants (`/api/openings/{id}/applicants`):** `HTTP 200 OK` (Retrieved 3 candidates with 10-competency scores)
- **Stage 5 Final Recommendations (`/api/interview/final-recommendations/{id}`):** `HTTP 200 OK` (Retrieved ranked cohort with composite scores)
- **Student Applications (`/api/applications/student/my-applications`):** `HTTP 200 OK`
- **Interview Slots (`/api/interview/slots/{id}`):** `HTTP 200 OK` (Retrieved 8 slots)

### C. Frontend Route Rendering Tests
All Next.js routes responded with `HTTP 200 OK`:
- `http://localhost:3000/` &rarr; `HTTP 200 OK`
- `http://localhost:3000/teacher/dashboard` &rarr; `HTTP 200 OK`
- `http://localhost:3000/student/openings` &rarr; `HTTP 200 OK`
- `http://localhost:3000/student/applications` &rarr; `HTTP 200 OK`
- `http://localhost:3000/teacher/create-opening` &rarr; `HTTP 200 OK`
- `http://localhost:3000/teacher/openings/f04f741c-0128-4cb7-8ba1-796b14e47b15/applications` &rarr; `HTTP 200 OK`
- `http://localhost:3000/student/interview/40810b7c-19ce-4f89-a36d-465dfeb35e52` &rarr; `HTTP 200 OK`

---

## 5. Commands to Start and Operate the Project

```bash
# 1. Start MySQL and Backend
docker compose up -d mysql backend

# 2. Check Backend Health
curl http://localhost:8000/api/health

# 3. Seed Demo Data (Populates Recruiter Opening, Candidates, Scores, and Turn Logs)
docker exec -i interview_backend python3 seed_demo_data.py

# 4. Verify Frontend is Serving
curl -sI http://localhost:3000
# If frontend is not running:
cd frontend && npm run start
```

### Demonstration Credentials
- **Recruiter Login:** `prof_turing@iiitdwd.ac.in` | **Password:** `Password123!`
- **Candidate Login:** `alex.mercer@gmail.com` | **Password:** `Password123!`
- **Portal URL:** `http://localhost:3000`

---

<<<<<<< HEAD
---

## 7. Stage 4 — AI Voice Interview Question Visibility Fix (November 11, 2026)

### A. Problem Description
When a candidate entered the interview page, the interview question was not appearing on screen. The candidate was left with a blank or uninformative screen, unable to see what question to answer.

### B. Root Cause Analysis
1. **Absence of Dedicated Current Question State & Prominent UI Card:**
   The frontend previously rendered questions strictly within a scrollable `messages.map` list. There was no dedicated `currentQuestion` state variable and no prominent card. During initial session setup or while the AI was generating questions, `messages` was `[]`, resulting in an empty dialogue container without any card or prompt.
2. **Missing AI Thinking / Formulating Indicator:**
   When identity verification passed, `setIdentityVerified(true)` was invoked immediately, transitioning to Stage 4 while `await fetch("/api/interview/start")` was still in flight (taking 2–6 seconds for OpenRouter LLM generation in LangGraph). With no loading or thinking indicator in the chat area, the candidate stared at an empty screen.
3. **Loss of Question and History on State Updates / Re-renders:**
   `ttsEnabled` was erroneously placed in the dependency array of `checkGateAndFetch`'s `useEffect`. Toggling the audio mute button caused the entire session fetch to re-trigger, re-calling `/api/interview/start` and wiping out all previous candidate answers (`setMessages([{ sender: "AI", content: data.current_question }])`).
4. **Backend Message History & Decision Truncation:**
   Neither `start_interview_session` nor `submit_candidate_answer` returned the full `messages` history in `InterviewTurnResponse`. On page refresh or resumption, prior turns were absent from the API response. Additionally, `agentic_action` was missing from `InterviewTurnResponse`.
5. **Lack of Fallback for Null/Empty Questions:**
   If the LLM returned empty content or hit a timeout, `current_question` could become `""` or `None`, which caused the frontend to bypass `setMessages`, leaving the chat permanently blank without error notification.

### C. Files Changed & Technical Fixes
1. **`backend/schemas/interview_schemas.py`:**
   - Added `turn_feedback: Optional[Dict[str, Any]] = None` to `InterviewMessageResponse`.
   - Added `agentic_action: Optional[str] = None` and `messages: Optional[List[InterviewMessageResponse]] = None` to `InterviewTurnResponse`.
2. **`backend/controllers/interview_controller.py`:**
   - In `start_interview_session`: Guaranteed non-empty fallback question for new sessions; fetched all `InterviewMessage` records for existing sessions; returned synchronized `messages` and `agentic_action`.
   - In `submit_candidate_answer`: Guaranteed non-empty next question; populated full `messages` history and `agentic_action` for both in-progress and concluding turns.
3. **`backend/services/interview_agent.py`:**
   - Guaranteed non-empty question outputs in `generate_question_node` and `perceive_evaluate_node`, preventing empty string propagation to state and database.
4. **`frontend/app/student/interview/[applicationId]/page.tsx`:**
   - Introduced dedicated states: `currentQuestion`, `questionLoading`, `currentDecision`, `latestReasoning`, `showHistory`.
   - Replaced `ttsEnabled` in `checkGateAndFetch` dependencies with `ttsEnabledRef` to prevent re-fetch and message wipeout on audio toggle.
   - Built a **Prominent Current Question Card** at the top of the interview area with turn progress (`Question X of Y`), dynamic decision badge (`Broad Competency Pivot`, `Targeted Follow-up`, `Opening Question`), audio playback button (`Read Aloud`), and an active pulsing AI Thinking indicator (`AI Interviewer is formulating Question X...`).
   - Built a dedicated **Candidate Answer Input Card** with voice dictation toggle (`🎙️ Speak Answer` / `⏹ Stop Mic`), live multi-line textarea, word count, and loading state.
   - Built a collapsible **Interview Transcript & History** section displaying all prior questions, candidate answers, turn scores, and AI reasoning logs.
   - Ensured page refresh seamlessly restores active interview state, current question, and transcript history.

### D. Verification & Test Results
- **Automated Regression Suite (`test_pipeline_e2e.py`):**
  - All 5 stages executed end-to-end with 100% pass rate.
  - Stage 4 verified dynamic question formulation, candidate answer evaluation, emergent mentorship pivot to `leadership_mentorship`, and final report generation.
- **Dedicated Candidate Session Test:**
  - Registered candidate Jordan Lee, verified identity at Stage 3 gate (`PASS`), started interview:
    - `FIRST INTERVIEW QUESTION:` Dynamically formulated and verified non-empty.
    - Candidate submitted answer: AI evaluated turn (`Score: 40.0`), formulated `narrow_follow_up` question regarding data distribution and fault tolerance.
    - Verified page reload cleanly returns status 200, current question, and all 3 transcript messages.
- **Frontend Production Build:**
  - `npm run build` compiled with Turbopack in under 900ms with zero errors. All routes verified.

=======
## 6. Remaining Issues

- **None.** The backend container is healthy and auto-reloads safely without crashing. The frontend communicates with the backend on both `localhost` and `127.0.0.1` without CORS or network errors. All five pipeline stages are fully operational.
>>>>>>> origin/main

