# Project 7: End-to-End AI Hiring Pipeline — Manual Testing Report

**Date of Testing:** November 10, 2026  
**Testing Mode:** Interactive Manual Verification (User-Driven)  
**Status:** IN PROGRESS  

---

## 1. Environment & Services Confirmation

| Component | Endpoint | Status | Verified |
|---|---|---|---|
| **FastAPI Backend** | `http://localhost:8000` | Running / Healthy | Yes |
| **MySQL 8.0 Database** | `localhost:3306` | Running / Healthy | Yes |
| **Next.js 16 Frontend** | `http://localhost:3000` | Running / Healthy | Yes |

---

## 2. Interactive Testing Checklist & Results

### Part A: Recruiter Workflow

| Step | Test Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| **R1** | **Recruiter Login** (`/`) with `prof_turing@iiitdwd.ac.in` | Authenticates and redirects to `/teacher/dashboard`. | In Progress | ⏳ Pending |
| **R2** | **Dashboard View** (`/teacher/dashboard`) | Displays active openings, metrics, and navigation buttons. | — | ⏳ Pending |
| **R3** | **Create Opening** (`/teacher/create-opening`) | Submits title, department, prerequisites, syllabus, and publishes opening. | — | ⏳ Pending |
| **R4** | **View Opening Applicants** (`/teacher/openings/[id]/applications`) | Renders applicant cards with GPA, GATE, status, and resume links. | — | ⏳ Pending |
| **R5** | **Inspect Resume Scoring (10 Competencies)** | Displays 10-competency breakdown with evidence quotes and analyses. | — | ⏳ Pending |
| **R6** | **Shortlist Execution** | Evaluates resumes and assigns `SHORTLISTED` / `REJECTED` statuses. | — | ⏳ Pending |
| **R7** | **Interview Slots Allocation** | Displays generated interview time slots for shortlisted candidates. | — | ⏳ Pending |
| **R8** | **Schedule Confirmation** | Confirms slot booking with mock calendar details (`cal_<id>`). | — | ⏳ Pending |
| **R9** | **Turn Reasoning Logs Inspection** | Recruiter opens modal inspecting turn-by-turn agent deliberation and decisions. | — | ⏳ Pending |
| **R10** | **Final Recommendations & Ranking (Stage 5)** | Displays cohort rankings (#1, #2, #3...), composite scores (40/60), and verdicts. | — | ⏳ Pending |

---

### Part B: Candidate Workflow

| Step | Test Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| **C1** | **Candidate Login** (`/`) with `alex.mercer@gmail.com` | Authenticates and redirects to `/student/openings`. | — | ⏳ Pending |
| **C2** | **Browse Openings** (`/student/openings`) | Lists published job openings with department and criteria. | — | ⏳ Pending |
| **C3** | **Apply for Opening** | Uploads PDF/DOCX resume, enters GPA, and submits application. | — | ⏳ Pending |
| **C4** | **Track Applications** (`/student/applications`) | Displays status badges (`APPLIED`, `SHORTLISTED`, `INTERVIEW_PENDING`). | — | ⏳ Pending |
| **C5** | **Select & Book Slot** | Selects an available slot and receives confirmation modal. | — | ⏳ Pending |
| **C6** | **Identity Hard Gate Chamber** (`/student/interview/[id]`) | Displays webcam feed, targeting reticle, and blocks interview until verified. | — | ⏳ Pending |
| **C7** | **Pass Facial Verification** | SFace compares live webcam frame to reference photo and unlocks interview. | — | ⏳ Pending |
| **C8** | **AI Voice Interview Interaction** | Listens to TTS question, records voice response (STT) or typed fallback. | — | ⏳ Pending |
| **C9** | **Emergent Broad Pivot Response** | Speaks answer with mentorship trigger; verifies agent pivots to `leadership_mentorship`. | — | ⏳ Pending |
| **C10**| **Interview Completion & Report** | Finishes all turns, displays session completion status and evaluation. | — | ⏳ Pending |

---

### Part C: Negative & Failure Testing

| Step | Test Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| **F1** | **Invalid Credentials** | Error banner: *"Invalid email or password"*. | — | ⏳ Pending |
| **F2** | **Invalid Resume Format** | Rejects non-PDF/DOCX file with 400 Bad Request. | — | ⏳ Pending |
| **F3** | **Duplicate Slot Booking** | Rejects double-booking attempt with HTTP 409 Conflict. | — | ⏳ Pending |
| **F4** | **Zero Faces Detected** | Obscured camera triggers `FAIL` and blocks interview entry. | — | ⏳ Pending |
| **F5** | **Multiple Faces Detected** | Two people in camera triggers integrity violation and blocks entry. | — | ⏳ Pending |
| **F6** | **Face Identity Mismatch** | Different person fails cosine threshold and routes to human review. | — | ⏳ Pending |
| **F7** | **Direct Entry Bypass Attempt** | Unverified candidate accessing interview session gets 403 Forbidden. | — | ⏳ Pending |

---

## 3. Log of Completed Test Steps

*(Entries will be recorded chronologically as each step is verified).*

