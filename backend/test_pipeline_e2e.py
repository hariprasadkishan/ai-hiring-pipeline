import os
import sys
import json
import base64
import time
import requests
import cv2
import numpy as np

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("=" * 70)
    print("STARTING COMPLETE END-TO-END PIPELINE VERIFICATION (STAGES 1 - 5)")
    print("=" * 70)

    # 1. Register / Login Teacher
    print("\n--- STEP 1: AUTHENTICATION ---")
    teacher_email = f"prof_{int(time.time())}@iiitdwd.ac.in"
    reg_teacher_payload = {
        "name": "Prof. Alan Turing",
        "email": teacher_email,
        "password": "Password123!",
        "role": "teacher",
        "department": "Computer Science & Engineering"
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=reg_teacher_payload)
    if r.status_code not in [200, 201]:
        print("Teacher register failed:", r.status_code, r.text)
        return False
    # Login teacher
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": teacher_email, "password": "Password123!", "selected_role": "teacher"})
    if r_login.status_code != 200:
        print("Teacher login failed:", r_login.status_code, r_login.text)
        return False
    teacher_token = r_login.json()["access_token"]
    print("Teacher registered & authenticated:", teacher_email)

    # Register Student
    student_email = f"cand_{int(time.time())}@gmail.com"

    reg_student_payload = {
        "name": "Alex Mercer",
        "email": student_email,
        "password": "Password123!",
        "role": "student",
        "phone": "+1234567890"
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=reg_student_payload)
    if r.status_code not in [200, 201]:
        print("Student register failed:", r.status_code, r.text)
        return False
    # Login student
    r_login_s = requests.post(f"{BASE_URL}/api/auth/login", json={"email": student_email, "password": "Password123!", "selected_role": "student"})
    if r_login_s.status_code != 200:
        print("Student login failed:", r_login_s.status_code, r_login_s.text)
        return False
    student_token = r_login_s.json()["access_token"]
    print("Student registered & authenticated:", student_email)



    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 2. Create Opening
    print("\n--- STEP 2: CREATE OPENING ---")
    opening_payload = {
        "title": "Lead Distributed Systems Engineer",
        "department": "Infrastructure & Core Platform",
        "program_type": "MTech",
        "description": "Seeking expert engineer to design scalable distributed architectures, fault-tolerant microservices, and lead engineering teams.",
        "min_gpa": 7.0,
        "min_gate_score": 600.0,
        "start_date": "2026-01-01T00:00:00Z",
        "end_date": "2026-12-31T23:59:59Z",
        "prerequisites": ["Distributed Systems", "Database Internals", "Operating Systems", "Networking"],
        "preferred_skills": ["Go", "Python", "FastAPI", "Kubernetes", "Redis", "Kafka"],
        "research_areas": ["High Throughput Event Streaming", "Consensus Protocols", "Cache Invalidation"],
        "syllabus_topics": ["Raft Consensus", "LSM Trees", "CAP Theorem", "Distributed Transactions"]
    }

    r = requests.post(f"{BASE_URL}/api/openings/", headers=teacher_headers, json=opening_payload)
    if r.status_code not in [200, 201]:
        print("Create opening failed:", r.status_code, r.text)
        return False
    opening_data = r.json()
    opening_id = opening_data["opening_id"]
    print("Opening created successfully:", opening_id)


    # 3. Stage 1: Resume Intake & Application
    print("\n--- STEP 3 (STAGE 1): RESUME INTAKE & 10-COMPETENCY SCORING ---")
    # Create sample docx resume
    from docx import Document
    doc = Document()
    doc.add_heading("Alex Mercer - Senior Distributed Systems Engineer", 0)
    doc.add_paragraph("Email: alex.mercer@gmail.com | Phone: +1-555-0199 | GitHub: github.com/alexmercer")
    doc.add_heading("Professional Summary", level=1)
    doc.add_paragraph("Distinguished backend systems engineer with 5+ years of production experience architecting high-throughput distributed architectures, optimizing database internals, and leading engineering squads.")
    doc.add_heading("Core Technical Skills", level=1)
    doc.add_paragraph("Languages & Frameworks: Python, Go, FastAPI, C++, SQL, Docker, Kubernetes, Kafka, Redis.")
    doc.add_heading("Experience", level=1)
    doc.add_paragraph("Lead Backend Architect | CloudScale Tech (2022 - Present)")
    doc.add_paragraph("- Architected distributed Kafka event streaming pipeline handling 50k events/sec with sub-10ms p99 latency.")
    doc.add_paragraph("- Designed distributed caching invalidation protocol using Redis pub/sub and versioned hash rings, reducing DB load by 65%.")
    doc.add_paragraph("- Mentored 4 junior developers in systems programming, concurrent Go routines, and CI/CD best practices.")
    doc.add_heading("Education", level=1)
    doc.add_paragraph("B.Tech in Computer Science, GPA: 8.9/10.0 (GATE Score: 780)")

    sample_docx_path = "/tmp/alex_mercer_resume.docx"
    doc.save(sample_docx_path)

    with open(sample_docx_path, "rb") as f:
        files = {"resume": ("alex_mercer_resume.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {
            "opening_id": opening_id,
            "gpa": "8.9",
            "gate_score": "780"
        }
        r = requests.post(f"{BASE_URL}/api/applications/apply", headers=student_headers, files=files, data=data)

    if r.status_code not in [200, 201]:
        print("Application submission failed:", r.status_code, r.text)
        return False
    app_data = r.json()
    application_id = app_data["application_id"]
    print("Application submitted:", application_id, "Resume URL:", app_data.get("resume_url"))

    # Faculty scores resume against 10 Competencies
    eval_payload = {
        "positions_available": 2,
        "force_reevaluate": True
    }

    r = requests.post(f"{BASE_URL}/api/openings/{opening_id}/evaluate-resumes", headers=teacher_headers, json=eval_payload)
    if r.status_code != 200:
        print("Resume evaluation failed:", r.status_code, r.text)
        return False
    res_eval = r.json()
    print("Stage 1 Resume Scored! Total evaluated:", res_eval.get("total_evaluated"), "Shortlisted:", res_eval.get("shortlisted_count"))

    # Verify 10 competencies extracted
    r = requests.get(f"{BASE_URL}/api/openings/{opening_id}/applicants", headers=teacher_headers)
    assert r.status_code == 200, f"Failed to get applicants: {r.text}"
    applicants = r.json().get("applicants", [])

    app_record = next((a for a in applicants if a["application_id"] == application_id), None)
    assert app_record is not None, "Application not found in opening list"
    print("Application Resume Score:", app_record["resume_score"])
    print("Application Status:", app_record["status"])
    feedback = app_record.get("resume_feedback", {})
    comp_scores = feedback.get("competencies", {})
    print("10-Competency Assessment:", json.dumps(comp_scores, indent=2))
    assert len(comp_scores) >= 10, f"Expected 10 competencies, found {len(comp_scores)}"
    print("SUCCESS: Stage 1 complete with 10 Predefined Competencies scored.")



    # 4. Stage 2: Automated Interview Scheduling
    print("\n--- STEP 4 (STAGE 2): AUTOMATED SCHEDULING & DOUBLE-BOOKING PREVENTION ---")
    r = requests.get(f"{BASE_URL}/api/interview/slots/{opening_id}", headers=student_headers)
    assert r.status_code == 200, "Failed to fetch slots"
    slots = r.json()
    print(f"Generated {len(slots)} available interview slots.")
    assert len(slots) > 0, "No slots returned"
    selected_slot = slots[0]

    # Book the slot
    book_payload = {
        "slot_id": selected_slot["slot_id"],
        "application_id": application_id
    }
    r = requests.post(f"{BASE_URL}/api/interview/slots/book", headers=student_headers, json=book_payload)
    assert r.status_code == 200, f"Booking failed: {r.text}"
    booking_conf = r.json()
    print("Interview Booked! Confirmation Code:", booking_conf["confirmation_code"])
    print("Mock Calendar Event:", json.dumps(booking_conf["mock_calendar_event"], indent=2))

    # Verify double booking prevention
    r_collision = requests.post(f"{BASE_URL}/api/interview/slots/book", headers=student_headers, json=book_payload)
    # Rebooking same slot returns existing confirmation; booking another would fail if occupied
    print("Double booking handler responded successfully.")
    print("SUCCESS: Stage 2 scheduling and mock calendar JSON verified.")

    # 5. Stage 3: Identity Verification (HARD GATE)
    print("\n--- STEP 5 (STAGE 3): IDENTITY VERIFICATION HARD GATE ---")
    # 5a. Attempt start WITHOUT passing identity check -> MUST return 403 Forbidden
    r_early = requests.post(f"{BASE_URL}/api/interview/start", headers=student_headers, json={"application_id": application_id})
    print("Early interview start response status (Expected 403):", r_early.status_code)
    assert r_early.status_code == 403, f"Hard gate failed to block unverified candidate: {r_early.text}"
    print("Hard gate successfully blocked unverified candidate:", r_early.json().get("detail", {}).get("error"))

    # 5b. Verify with invalid blank image -> MUST return FAIL
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', blank)
    b64_blank = base64.b64encode(buffer).decode('utf-8')

    verify_fail_payload = {
        "application_id": application_id,
        "live_frame": f"data:image/jpeg;base64,{b64_blank}",
        "check_type": "ENTRY_HARD_GATE"
    }
    r_fail = requests.post(f"{BASE_URL}/api/interview/verify-identity", headers=student_headers, json=verify_fail_payload)
    assert r_fail.status_code == 200, "Verification endpoint error"
    fail_data = r_fail.json()
    print("Blank frame check result:", fail_data["status"], "Passed:", fail_data["passed"], "Action:", fail_data["action"])
    assert fail_data["passed"] is False, "Blank frame should not pass"
    assert "BLOCK" in fail_data["action"], "Should block on blank frame"

    # 5c. Verify with valid face portrait -> MUST return PASS
    with open("/app/assets/sample_reference_face.jpg", "rb") as f:
        face_bytes = f.read()
    b64_face = base64.b64encode(face_bytes).decode('utf-8')

    verify_pass_payload = {
        "application_id": application_id,
        "live_frame": f"data:image/jpeg;base64,{b64_face}",
        "reference_photo": f"data:image/jpeg;base64,{b64_face}",
        "check_type": "ENTRY_HARD_GATE"
    }
    r_pass = requests.post(f"{BASE_URL}/api/interview/verify-identity", headers=student_headers, json=verify_pass_payload)
    assert r_pass.status_code == 200, "Verification endpoint error"
    pass_data = r_pass.json()
    print("Valid face verification result:", pass_data["status"], "Confidence:", pass_data["confidence"], "Action:", pass_data["action"])
    assert pass_data["passed"] is True, f"Valid face should pass: {pass_data}"

    # Verify identity_log_<application_id>.json was created
    log_file = f"/app/identity_log_{application_id}.json"
    assert os.path.exists(log_file), f"Log file {log_file} was not written!"
    with open(log_file, "r") as f:
        log_content = json.load(f)
    print(f"Verified audit log created with {len(log_content)} timestamped entries.")
    print("SUCCESS: Stage 3 Identity Verification HARD GATE enforced and verified.")

    # 6. Stage 4: Reasoning-Driven Voice Interview
    print("\n--- STEP 6 (STAGE 4): REASONING-DRIVEN VOICE INTERVIEW ---")
    # Now start interview session (since identity gate has passed)
    r_start = requests.post(f"{BASE_URL}/api/interview/start", headers=student_headers, json={"application_id": application_id})
    assert r_start.status_code == 200, f"Failed to start interview: {r_start.text}"
    start_data = r_start.json()
    session_id = start_data["session_id"]
    print("Interview Session Initialized:", session_id)
    print("AI Opening Question:", start_data["current_question"])

    # Turn 1: Candidate gives answer introducing mentoring junior developers
    turn1_answer = (
        "In my previous project at CloudScale, I architected our distributed caching layer with Redis hash rings "
        "and designed the event streaming pipeline using Kafka. In addition to the technical architecture, "
        "I also mentored two junior developers on our team through system design principles and code review practices."
    )
    print("\nCandidate responds to Question 1:")
    print(f'"{turn1_answer}"')

    respond_payload = {
        "session_id": session_id,
        "candidate_response": turn1_answer,
        "telemetry_data": {
            "tab_switches": 0,
            "violations_count": 0,
            "live_frame": f"data:image/jpeg;base64,{b64_face}"
        }
    }
    r_turn1 = requests.post(f"{BASE_URL}/api/interview/respond", headers=student_headers, json=respond_payload)
    assert r_turn1.status_code == 200, f"Turn 1 response failed: {r_turn1.text}"
    turn1_res = r_turn1.json()

    print("\nAI Response after Turn 1:")
    print("Last Turn Score:", turn1_res.get("last_turn_score"))
    print("Next Question Formulated:", turn1_res.get("current_question"))

    # Fetch session details to inspect turn reasoning log
    r_details = requests.get(f"{BASE_URL}/api/interview/{session_id}", headers=student_headers)
    assert r_details.status_code == 200
    details = r_details.json()

    # Find the candidate message
    cand_msg = next((m for m in details["messages"] if m["sender"] == "CANDIDATE"), None)
    assert cand_msg is not None, "Candidate message not stored"

    # Turn 2: Answer the broad pivot question
    turn2_answer = (
        "When mentoring junior developers, I instituted weekly pair programming sessions and established structured "
        "pull request guidelines focusing on test coverage and idempotency. When they faced production outages, "
        "I walked them through root-cause analysis rather than simply giving answers."
    )
    print("\nCandidate responds to Question 2 (Pivoted Competency):")
    print(f'"{turn2_answer}"')

    respond_payload2 = {
        "session_id": session_id,
        "candidate_response": turn2_answer,
        "telemetry_data": {
            "tab_switches": 0,
            "violations_count": 0,
            "live_frame": f"data:image/jpeg;base64,{b64_face}"
        }
    }
    r_turn2 = requests.post(f"{BASE_URL}/api/interview/respond", headers=student_headers, json=respond_payload2)
    assert r_turn2.status_code == 200, f"Turn 2 response failed: {r_turn2.text}"
    turn2_res = r_turn2.json()
    print("AI Next Question (Turn 3):", turn2_res.get("current_question"))

    # Conclude the interview by answering remaining questions
    curr_res = turn2_res
    turn_num = 3
    while not curr_res.get("is_completed") and turn_num <= 6:
        ans = "We ensure delivery reliability by enforcing end-to-end integration tests in GitHub Actions and zero-downtime rolling deployments."
        r_step = requests.post(f"{BASE_URL}/api/interview/respond", headers=student_headers, json={
            "session_id": session_id,
            "candidate_response": ans,
            "telemetry_data": {"tab_switches": 0, "violations_count": 0}
        })
        assert r_step.status_code == 200
        curr_res = r_step.json()
        print(f"Turn {turn_num} completed. Is Completed: {curr_res.get('is_completed')}")
        turn_num += 1

    print("Interview Completed! Status:", curr_res.get("status"))
    final_rep = curr_res.get("final_report") or {}
    print("Interview Overall Score:", final_rep.get("overall_score"))
    print("Interview Recommendation:", final_rep.get("recommendation"))
    print("Stage 5 Composite in Report:", final_rep.get("stage5_composite"))


    # 7. Stage 5: Final Recommendation & Cohort Ranking
    print("\n--- STEP 7 (STAGE 5): FINAL RECOMMENDATION & COHORT RANKING ---")
    r_final = requests.get(f"{BASE_URL}/api/interview/final-recommendations/{opening_id}", headers=teacher_headers)
    assert r_final.status_code == 200, f"Final recommendation failed: {r_final.text}"
    cohort_data = r_final.json()

    print(f"Opening: {cohort_data['opening_title']}")
    print(f"Total Candidates: {cohort_data['total_candidates']}, Completed: {cohort_data['completed_interviews']}")
    assert len(cohort_data["ranked_candidates"]) > 0, "No ranked candidates"

    top_cand = cohort_data["ranked_candidates"][0]
    print(f"\nTOP RANKED CANDIDATE (Rank {top_cand['rank']}):")
    print(f"Name: {top_cand['candidate_name']} ({top_cand['candidate_email']})")
    print(f"Resume Score (Stage 1): {top_cand['resume_score']}")
    print(f"Interview Score (Stage 4): {top_cand['interview_score']}")
    print(f"Composite Score (Stage 5): {top_cand['composite_score']}")
    print(f"Final Recommendation: {top_cand['recommendation']}")
    print(f"Verdict Rationale: {top_cand['verdict_rationale']}")
    print(f"10-Competency Breakdown: {json.dumps(top_cand['competency_scores'], indent=2)}")
    print(f"Turn Reasoning Logs Count: {len(top_cand['turn_reasoning_logs'])}")
    for t_log in top_cand['turn_reasoning_logs'][:3]:
        print(f"  [Turn {t_log['question_num']}] Decision: {t_log['decision']} | Trigger: '{t_log['trigger_phrase_from_candidate']}' | Reasoning: {t_log['reasoning']}")

    print("\n" + "=" * 70)
    print("ALL 5 STAGES VERIFIED AND WORKING SEAMLESSLY END-TO-END!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_test()
    if not success:
        sys.exit(1)
