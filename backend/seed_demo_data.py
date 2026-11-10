import os
import sys
import uuid
import datetime
import json
from database import SessionLocal
from models.user import User, TeacherProfile, StudentProfile
from models.opening import AdmissionOpening
from models.application import Application
from models.interview import InterviewSession, InterviewMessage, InterviewSlot, InterviewSessionStatus, MessageSender
from utils.security import hash_password

def seed():
    db = SessionLocal()
    print("=" * 60)
    print("SEEDING DEMONSTRATION DATA FOR AI HIRING PIPELINE")
    print("=" * 60)

    try:
        # 1. Recruiter User
        teacher_email = "prof_turing@iiitdwd.ac.in"
        teacher_user = db.query(User).filter(User.email == teacher_email).first()
        if not teacher_user:
            teacher_user = User(
                user_id=str(uuid.uuid4()),
                name="Prof. Alan Turing",
                email=teacher_email,
                password_hash=hash_password("Password123!"),
                role="teacher"
            )
            db.add(teacher_user)
            db.flush()
            t_profile = TeacherProfile(
                teacher_id=str(uuid.uuid4()),
                user_id=teacher_user.user_id,
                department="Computer Science & Engineering"
            )
            db.add(t_profile)
            db.flush()
        else:
            t_profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == teacher_user.user_id).first()

        print(f"Recruiter ready: {teacher_email} (Password: Password123!)")

        # 2. Hiring Opening
        opening_title = "Senior AI & Distributed Systems Engineer"
        opening = db.query(AdmissionOpening).filter(AdmissionOpening.title == opening_title).first()
        now = datetime.datetime.utcnow()
        if not opening:
            opening = AdmissionOpening(
                opening_id=str(uuid.uuid4()),
                teacher_id=t_profile.teacher_id,
                program_type="PhD",
                title=opening_title,
                department="Computer Science & Engineering",
                description="Lead architectural development for real-time distributed AI training pipelines and high-throughput inference engines.",
                research_areas=["Distributed Systems", "Machine Learning Infrastructure", "Event Streaming"],
                preferred_skills=["FastAPI", "Go", "Docker", "Kubernetes", "Kafka", "PyTorch", "Redis"],
                min_gpa=7.0,
                min_gate_score=650.0,
                prerequisites=["Distributed Systems", "Database Internals", "Concurrent Programming"],
                syllabus_topics=["Raft Consensus", "LSM Trees", "Kafka Architecture", "Distributed Caching"],
                start_date=now - datetime.timedelta(days=2),
                end_date=now + datetime.timedelta(days=30)
            )
            db.add(opening)
            db.flush()

        print(f"Opening ready: {opening.title} (ID: {opening.opening_id})")

        # 3. Create Interview Slots
        existing_slots = db.query(InterviewSlot).filter(InterviewSlot.opening_id == opening.opening_id).all()
        slots = []
        if not existing_slots:
            for i in range(1, 9):
                slot_time = now + datetime.timedelta(days=2, hours=9 + i)
                s = InterviewSlot(
                    slot_id=str(uuid.uuid4()),
                    opening_id=opening.opening_id,
                    start_time=slot_time,
                    end_time=slot_time + datetime.timedelta(minutes=45),
                    is_booked=False
                )
                db.add(s)
                slots.append(s)
            db.flush()
        else:
            slots = existing_slots

        print(f"Slots ready: {len(slots)} interview slots created.")

        # 4. Candidates to Seed
        candidates = [
            {
                "name": "Alex Mercer",
                "email": "alex.mercer@gmail.com",
                "phone": "+1-555-0199",
                "gpa": 8.9,
                "gate_score": 780.0,
                "resume_score": 85.0,
                "interview_score": 88.0,
                "status": "COMPLETED",
                "recommendation": "RECOMMENDED",
                "competency_scores": {
                    "technical_depth": 88.0,
                    "system_architecture": 86.0,
                    "problem_solving": 90.0,
                    "communication": 82.0,
                    "leadership_mentorship": 85.0,
                    "adaptability": 84.0,
                    "domain_expertise": 88.0,
                    "collaboration": 85.0,
                    "analytical_reasoning": 87.0,
                    "delivery_reliability": 86.0
                },
                "turn_logs": [
                    {
                        "question_num": 1,
                        "decision": "narrow_follow_up",
                        "trigger_phrase_from_candidate": "architected distributed Kafka streaming pipeline handling 50k events/sec",
                        "reasoning": "Candidate highlighted a concrete high-throughput event streaming architecture. Probing deeper into partition sizing and backpressure guarantees.",
                        "question_asked": "How did you manage Kafka consumer group rebalances and handle partition skew under high event velocity?",
                        "score": 86.0
                    },
                    {
                        "question_num": 2,
                        "decision": "broad_pivot",
                        "trigger_phrase_from_candidate": "instituted pair programming sessions and mentored two junior developers",
                        "reasoning": "Candidate introduced team mentorship and engineering guidance. Pivoting to explore leadership and mentorship capabilities.",
                        "question_asked": "Could you walk us through a specific technical disagreement you guided a junior developer through and how you helped them reach the right solution independently?",
                        "score": 89.0
                    },
                    {
                        "question_num": 3,
                        "decision": "broad_pivot",
                        "trigger_phrase_from_candidate": "enforced end-to-end integration tests in CI/CD with zero-downtime canary rollouts",
                        "reasoning": "Candidate detailed production deployment safety and automated test coverage. Probing delivery reliability practices.",
                        "question_asked": "How do your canary deployment thresholds detect silent regression errors in production before complete rollouts?",
                        "score": 88.0
                    },
                    {
                        "question_num": 4,
                        "decision": "conclude",
                        "trigger_phrase_from_candidate": "monitored automated rollback telemetry via Prometheus alert rules",
                        "reasoning": "Candidate demonstrated exceptional end-to-end mastery across architecture, leadership, and production delivery.",
                        "question_asked": "Thank you Alex. You have demonstrated rigorous technical depth and leadership. Our hiring committee will review the final synthesized report.",
                        "score": 90.0
                    }
                ]
            },
            {
                "name": "Sarah Chen",
                "email": "sarah.chen@gmail.com",
                "phone": "+1-555-0211",
                "gpa": 7.8,
                "gate_score": 690.0,
                "resume_score": 72.0,
                "interview_score": 64.0,
                "status": "COMPLETED",
                "recommendation": "BORDERLINE",
                "competency_scores": {
                    "technical_depth": 68.0,
                    "system_architecture": 65.0,
                    "problem_solving": 67.0,
                    "communication": 74.0,
                    "leadership_mentorship": 60.0,
                    "adaptability": 70.0,
                    "domain_expertise": 66.0,
                    "collaboration": 72.0,
                    "analytical_reasoning": 65.0,
                    "delivery_reliability": 62.0
                },
                "turn_logs": [
                    {
                        "question_num": 1,
                        "decision": "narrow_follow_up",
                        "trigger_phrase_from_candidate": "built microservices in Python using Docker",
                        "reasoning": "Provided high level summary of microservice deployment. Probing container networking and inter-service communication.",
                        "question_asked": "How did your microservices handle service discovery and circuit breaking during inter-service failure?",
                        "score": 65.0
                    },
                    {
                        "question_num": 2,
                        "decision": "next_competency",
                        "trigger_phrase_from_candidate": "we used basic retry loops with exponential backoff",
                        "reasoning": "Candidate explained standard retry logic adequately. Advancing agenda to distributed database transactions.",
                        "question_asked": "Let us examine your approach to maintaining data consistency across multiple databases without two-phase commit.",
                        "score": 63.0
                    }
                ]
            },
            {
                "name": "David Miller",
                "email": "david.miller@gmail.com",
                "phone": "+1-555-0344",
                "gpa": 6.8,
                "gate_score": 580.0,
                "resume_score": 55.0,
                "interview_score": 42.0,
                "status": "COMPLETED",
                "recommendation": "REJECTED",
                "competency_scores": {
                    "technical_depth": 45.0,
                    "system_architecture": 42.0,
                    "problem_solving": 40.0,
                    "communication": 50.0,
                    "leadership_mentorship": 40.0,
                    "adaptability": 48.0,
                    "domain_expertise": 42.0,
                    "collaboration": 49.0,
                    "analytical_reasoning": 41.0,
                    "delivery_reliability": 44.0
                },
                "turn_logs": [
                    {
                        "question_num": 1,
                        "decision": "narrow_follow_up",
                        "trigger_phrase_from_candidate": "mostly worked on frontend bug fixes and simple scripts",
                        "reasoning": "Candidate background reveals limited systems architecture experience. Probing foundational computer science concepts.",
                        "question_asked": "Could you explain the difference between a process and a thread, and how memory is shared between them?",
                        "score": 42.0
                    }
                ]
            }
        ]

        for idx, c_data in enumerate(candidates):
            c_user = db.query(User).filter(User.email == c_data["email"]).first()
            if not c_user:
                c_user = User(
                    user_id=str(uuid.uuid4()),
                    name=c_data["name"],
                    email=c_data["email"],
                    password_hash=hash_password("Password123!"),
                    role="student"
                )
                db.add(c_user)
                db.flush()
                c_profile = StudentProfile(
                    student_id=str(uuid.uuid4()),
                    user_id=c_user.user_id,
                    phone=c_data["phone"]
                )
                db.add(c_profile)
                db.flush()
            else:
                c_profile = db.query(StudentProfile).filter(StudentProfile.user_id == c_user.user_id).first()

            # Application
            app = db.query(Application).filter(
                Application.student_id == c_profile.student_id,
                Application.opening_id == opening.opening_id
            ).first()

            if not app:
                comp_breakdown = {
                    k: {"score": round(v / 10.0, 1), "evidence": f"Demonstrated evidence for {k} in candidate background.", "analysis": f"Strong competency evaluation for {k}."}
                    for k, v in c_data["competency_scores"].items()
                }
                app = Application(
                    application_id=str(uuid.uuid4()),
                    student_id=c_profile.student_id,
                    opening_id=opening.opening_id,
                    gpa=c_data["gpa"],
                    gate_score=c_data["gate_score"],
                    resume_url="https://res.cloudinary.com/demo/sample_resume.pdf",
                    resume_score=c_data["resume_score"],
                    resume_feedback={
                        "resume_score": c_data["resume_score"],
                        "competencies": comp_breakdown,
                        "summary_reasoning": f"Comprehensive profile intake across all 10 predefined competencies for {c_data['name']}."
                    },
                    status=c_data["status"]
                )
                db.add(app)
                db.flush()

            # Book a slot for candidate
            if idx < len(slots):
                target_slot = slots[idx]
                target_slot.is_booked = True
                target_slot.booked_by_application_id = app.application_id
                target_slot.confirmation_code = f"CONF-{c_data['name'].split()[0].upper()}{idx+101}"

            # Interview Session
            session = db.query(InterviewSession).filter(InterviewSession.application_id == app.application_id).first()
            if not session:
                session = InterviewSession(
                    session_id=str(uuid.uuid4()),
                    application_id=app.application_id,
                    status=InterviewSessionStatus.COMPLETED,
                    total_questions=len(c_data["turn_logs"]),
                    current_question_index=len(c_data["turn_logs"]),
                    overall_score=c_data["interview_score"],
                    evaluation_report={
                        "overall_score": c_data["interview_score"],
                        "recommendation": c_data["recommendation"],
                        "competency_scores": c_data["competency_scores"],
                        "turn_evaluations": c_data["turn_logs"],
                        "stage5_composite": {
                            "resume_score": c_data["resume_score"],
                            "interview_score": c_data["interview_score"],
                            "composite_score": round((c_data["resume_score"] * 0.40) + (c_data["interview_score"] * 0.60), 1),
                            "weight_resume": 0.40,
                            "weight_interview": 0.60
                        }
                    },
                    started_at=now - datetime.timedelta(hours=2),
                    completed_at=now - datetime.timedelta(hours=1)
                )
                db.add(session)
                db.flush()

                # Add messages
                for t in c_data["turn_logs"]:
                    msg_ai = InterviewMessage(
                        message_id=str(uuid.uuid4()),
                        session_id=session.session_id,
                        sender=MessageSender.AI,
                        question_num=t["question_num"],
                        content=t["question_asked"],
                        turn_score=t["score"],
                        turn_feedback=t
                    )
                    db.add(msg_ai)

            print(f"Seeded Candidate #{idx+1}: {c_data['name']} ({c_data['email']}) -> Composite: {round((c_data['resume_score']*0.4) + (c_data['interview_score']*0.6), 1)} ({c_data['recommendation']})")

        db.commit()
        print("=" * 60)
        print("SUCCESSFULLY SEEDED DEMO DATA!")
        print("Recruiter Login: prof_turing@iiitdwd.ac.in | Password: Password123!")
        print("Candidate Login: alex.mercer@gmail.com  | Password: Password123!")
        print(f"Opening ID: {opening.opening_id}")
        print("View Dashboard: http://localhost:3000")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
