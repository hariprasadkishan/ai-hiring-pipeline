# Project 7: End-to-End AI Hiring Pipeline — Live Demonstration Script

**Target Audience:** Capstone Evaluation Committee, External Examiners, Engineering Recruiters  
**Estimated Presentation Duration:** 10–12 Minutes  
**Demonstration Portal:** `http://localhost:3000`  
**Backend API Docs:** `http://localhost:8000/docs`  

---

## Act 1: Recruiter Opening Creation & Competency Intake (2 Minutes)

### 1.1 Recruiter Login
1. Open browser to `http://localhost:3000`.
2. Select role **Faculty / Recruiter**.
3. Sign in with credentials:
   - **Email:** `prof_turing@iiitdwd.ac.in`
   - **Password:** `Password123!`
4. Land on **Faculty Dashboard**.

### 1.2 Creating the Engineering Opening
1. Click **"+ Create New Opening"**.
2. Fill out the opening specifications:
   - **Title:** `Senior Distributed Systems Engineer`
   - **Department:** `Computer Science & Engineering`
   - **Program Type:** `PhD` (or `MTech`)
   - **Min GPA:** `7.5`
   - **Prerequisites:** `Distributed Systems, Operating Systems, Computer Networks`
   - **Syllabus Topics:** `Raft Consensus, LSM Trees, Kafka Streaming, Cache Invalidation`
3. Click **"Publish Opening"**. Notice immediate availability in the active openings list.

---

## Act 2: Candidate Application & Stage 1 Resume Intake (2 Minutes)

### 2.1 Candidate Registration
1. In an incognito window (or after logging out), navigate to `http://localhost:3000`.
2. Register as a **Student / Candidate**:
   - **Name:** `Alex Mercer`
   - **Email:** `alex.mercer@gmail.com`
   - **Password:** `Password123!`
   - **Phone:** `+1-555-0199`

### 2.2 Submitting Application with DOCX Resume & Reference Photo
1. Go to **"Explore Openings"**.
2. Click **"Apply Now"** on `Senior Distributed Systems Engineer`.
3. Provide:
   - **GPA:** `8.9`
   - **Upload Resume:** Attach `alex_mercer_resume.docx` (or `.pdf`).
4. Click **"Submit Application"**.
5. Document is stored in Cloudinary and immediately evaluated by the LLM against the **10 Predefined Competencies**.

### 2.3 Recruiter Inspection of Stage 1 Scoring
1. Switch back to the Recruiter window and navigate to the opening's **Applicants** page.
2. In the **"Stage 1: Resume Intake & Screening (10 Competencies)"** view:
   - Point out the **Resume Score (77.5 / 100)** and **SHORTLISTED** status.
   - Expand the **10 Predefined Competencies Breakdown**:
     - Highlight direct evidence quotes extracted from the resume (e.g. under `technical_depth`: *"Architected distributed Kafka event streaming pipeline handling 50k events/sec..."*).
     - Point out competency scores: `technical_depth` (8.0/10), `problem_solving` (8.5/10), `leadership_mentorship` (6.5/10).

---

## Act 3: Stage 2 Automated Scheduling & Collision Prevention (1.5 Minutes)

1. In the Candidate window, navigate to **"My Applications"**.
2. Notice the application status: **SHORTLISTED**.
3. Click **"Select Interview Slot"**.
4. View the generated interview slots. Click on an available slot (e.g., Nov 12, 10:00 AM – 10:45 AM) and click **"Confirm Booking"**.
5. Modal displays the **Booking Confirmation**:
   - **Confirmation Code:** `CONF-6BB6CAF3`
   - **Mock Calendar Event JSON:** Displays `cal_<id>`, summary, start/end timestamps, and virtual meeting link.
6. **Collision Prevention Demonstration:** Point out that under concurrent requests, database row-level locking (`with_for_update`) prevents double-booking, rejecting conflicting reservations with HTTP 409 Conflict.

---

## Act 4: Stage 3 Identity Verification HARD GATE (2.5 Minutes)

### 4.1 Demonstrating the Hard Gate Block
1. Candidate clicks **"Take AI Interview"**.
2. The browser renders the **Stage 3 Identity Verification Chamber**:
   - Live webcam feed with targeting reticle.
   - Reference photograph display.
   - Real-time status banner: `🔒 STATUS: IDENTITY_PENDING`.
3. Notice that the interview room chat is completely locked and inaccessible until verification passes.

### 4.2 Demonstrating Failure Scenario (Camera Covered)
1. Cover the webcam with a hand or piece of paper.
2. Click **"Verify Identity (Hard Gate)"**.
3. Point out the instant rejection:
   - Status: `❌ FAILED: No face detected in frame. Candidate must center face in camera.`
   - Action: `BLOCK_AND_ROUTE_TO_HUMAN_REVIEW`
   - Direct the examiners' attention to `identity_log_<id>.json` showing the recorded failed entry check.

### 4.3 Passing Verification with Deep Face Recognition
1. Center face clearly in camera frame.
2. Click **"Verify Identity (Hard Gate)"**.
3. Computer Vision pipeline processes the frame:
   - **YuNet** detects facial bounding box and 5 landmark points.
   - **SFace** extracts 128-D deep embedding and computes cosine similarity against reference photo.
   - Point out the success banner: `✅ VERIFIED: Identity verified successfully with 100% face match confidence.`
4. Click **"Proceed to Technical Interview"**. The gate unlocks and launches the interactive voice chamber.

---

## Act 5: Stage 4 Reasoning Voice Interview & Broad Pivots (3 Minutes)

### 5.1 Dynamic Opening & Voice Audio
1. The AI Interviewer speaks the dynamic opening question via Text-to-Speech (TTS):
   *"Good morning Alex Mercer, welcome to your technical interview... To begin, could you introduce yourself and walk us through the most technically complex engineering project you built?"*
2. Demonstrate the **"Mute / Unmute Voice Audio"** toggle and the **"Listen to Question"** replay button.

### 5.2 Candidate Turn 1 (Technical Depth Claim)
1. Click the microphone button **"Speak Answer"** (or use the typed fallback textarea).
2. Submit:
   *"In my previous role at CloudScale, I architected our distributed caching layer using Redis hash rings and designed our event streaming pipeline with Kafka. In addition to the technical architecture, I also mentored two junior developers on our team."*
3. The AI agent deliberates:
   - Decision: `narrow_follow_up`.
   - Probes technical claim: asks candidate to elaborate on Redis hash ring architecture challenges and trade-offs.

### 5.3 Candidate Turn 2 (Triggering the Broad Pivot)
1. Submit the following response:
   *"When mentoring junior developers, I instituted weekly pair programming sessions and established structured pull request guidelines focusing on test coverage and idempotency. When they faced production outages, I walked them through root-cause analysis rather than simply giving answers."*
2. **Observe the emergent AI behavior:**
   - The AI agent recognizes that the candidate introduced a new competency (`leadership_mentorship`).
   - Decision: **`broad_pivot`**.
   - Trigger phrase captured: *"When mentoring junior developers"*.
   - Dynamic Question: Rather than stubbornly asking another technical question, the AI asks:
     *"Can you describe a specific instance where you mentored a junior engineer through a complex technical problem, and how you balanced guidance with fostering their independent problem-solving skills?"*
3. Explain to the evaluation committee: *"This proves our agent does not follow a static decision tree—it dynamically pivots across the 10 competencies based on semantic reasoning."*

---

## Act 6: Stage 5 Final Recommendation & Cohort Ranking (1.5 Minutes)

1. Conclude the interview.
2. Return to the Recruiter window at `http://localhost:3000/teacher/openings/[opening_id]/applications`.
3. Switch to the tab: **"Stage 5: Final Recommendations & Ranked Shortlist"**.
4. Point out the comprehensive cohort view:
   - **Composite Score:** `58.4 / 100` computed strictly via $(77.5 \times 0.40) + (45.6 \times 0.60)$.
   - **Recommendation Badge:** `BORDERLINE` (or `RECOMMENDED`).
   - **Rank Medal:** Candidate is ranked **#1** in the cohort.
   - **10-Competency Aggregated Breakdown:** Visual score pills across all 10 competencies.
5. Click **"Inspect Turn Reasoning Logs"**:
   - The modal reveals turn-by-turn agent deliberation:
     - Turn 1: `narrow_follow_up` with reasoning notes.
     - Turn 2: `broad_pivot` to `leadership_mentorship` with exact candidate trigger phrase.
     - Turn 3: `broad_pivot` to `delivery_reliability`.
6. Conclude the presentation: *"We have demonstrated a complete, fully autonomous, 5-stage AI hiring pipeline combining computer vision biometric gating, atomic scheduling, emergent reasoning voice interviews, and cohort synthesis."*

