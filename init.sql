CREATE DATABASE IF NOT EXISTS admission_db;
USE admission_db;

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('teacher', 'student') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    teacher_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_profiles (
    student_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    phone VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admission_openings (
    opening_id VARCHAR(36) PRIMARY KEY,
    teacher_id VARCHAR(36) NOT NULL,
    program_type ENUM('MTech', 'PhD') NOT NULL,
    title VARCHAR(150) NOT NULL,
    department VARCHAR(100) NOT NULL,
    description TEXT,
    research_areas JSON,
    preferred_skills JSON,
    min_gpa FLOAT NOT NULL DEFAULT 6.0,
    min_gate_score FLOAT,
    prerequisites JSON NOT NULL,
    syllabus_topics JSON NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teacher_profiles(teacher_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applications (
    application_id VARCHAR(36) PRIMARY KEY,
    student_id VARCHAR(36) NOT NULL,
    opening_id VARCHAR(36) NOT NULL,
    gpa FLOAT NOT NULL,
    gate_score FLOAT,
    resume_url VARCHAR(500),
    resume_score FLOAT,
    resume_feedback JSON,
    status ENUM('APPLIED', 'SHORTLISTED', 'REJECTED', 'INTERVIEW_PENDING', 'ACCEPTED', 'COMPLETED') DEFAULT 'APPLIED' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE,
    FOREIGN KEY (opening_id) REFERENCES admission_openings(opening_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_slots (
    slot_id VARCHAR(36) PRIMARY KEY,
    opening_id VARCHAR(36) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_booked BOOLEAN DEFAULT FALSE NOT NULL,
    booked_by_application_id VARCHAR(36) UNIQUE,
    confirmation_code VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opening_id) REFERENCES admission_openings(opening_id) ON DELETE CASCADE,
    FOREIGN KEY (booked_by_application_id) REFERENCES applications(application_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    application_id VARCHAR(36) UNIQUE NOT NULL,
    status ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED', 'TERMINATED_ABNORMALLY') DEFAULT 'PENDING' NOT NULL,
    total_questions INT DEFAULT 5 NOT NULL,
    current_question_index INT DEFAULT 0 NOT NULL,
    overall_score FLOAT,
    evaluation_report JSON,
    termination_reason VARCHAR(100),
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_messages (
    message_id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    sender ENUM('AI', 'CANDIDATE') NOT NULL,
    question_num INT NOT NULL,
    content TEXT NOT NULL,
    turn_score FLOAT,
    turn_feedback JSON,
    telemetry_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
);
