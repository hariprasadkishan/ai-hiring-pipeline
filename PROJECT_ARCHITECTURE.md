# Project 7: End-to-End AI Hiring Pipeline — Architecture Documentation

**System:** AI-Driven Technical Hiring Pipeline & Autonomous Interview Platform  
**Version:** 2.0 (Production / Capstone Final Delivery)  

---

## 1. High-Level System Architecture

The application is structured into five loosely coupled, highly integrated tiers:
1. **Presentation Tier:** Next.js 16 (React 19 App Router) providing dedicated recruiter and candidate portals with real-time audio/visual capture.
2. **Application Tier:** FastAPI (Python 3.11 ASGI) exposing RESTful endpoints, auth security, and business controllers.
3. **Agent & Intelligence Tier:** LangGraph-driven state-machine agent backed by OpenRouter LLMs for dynamic semantic interview deliberation.
4. **Biometric Computer Vision Tier:** OpenCV Deep Neural Network engine executing **YuNet** (face detection & 5-point landmark alignment) and **SFace** (128-dimensional deep face embedding extraction and cosine similarity verification).
5. **Persistence & Asset Tier:** MySQL 8.0 relational database (InnoDB engine with row-level locking) and Cloudinary raw/secure document storage.

```mermaid
flowchart TD
    subgraph Frontend["Frontend Tier (Next.js 16 / React 19)"]
        RecruiterUI["Recruiter Portal (Dashboards, Stage 1 Screening & Stage 5 Ranking)"]
        CandidateUI["Candidate Portal (Application, Slot Booking, Hard Gate Chamber, Voice Interview)"]
        WebcamStream["Webcam Stream & Biometric Target Canvas"]
        AudioEngine["Web Speech API (STT) + SpeechSynthesis (TTS)"]
    end

    subgraph Backend["Backend API Tier (FastAPI / Uvicorn)"]
        AuthCtrl["Auth & RBAC Controller (JWT)"]
        OpeningCtrl["Opening & Intake Controller"]
        ScheduleCtrl["Automated Scheduling Controller (with_for_update Row Lock)"]
        BioCtrl["Biometric Identity Verification Service"]
        AgentCtrl["Interactive Interview Agent Controller"]
        FinalRankCtrl["Composite Cohort Ranking Service"]
    end

    subgraph VisionEngine["Computer Vision & Face Recognition Engine"]
        YuNet["YuNet Face Detector & Landmark Aligner (ONNX)"]
        SFace["SFace MobileFaceNet 128-D Embedding Recognizer (ONNX)"]
        CosineMatch["Cosine Similarity Engine (Threshold: 0.363)"]
    end

    subgraph Intelligence["Agentic Intelligence Tier"]
        LangGraphAgent["LangGraph StateGraph"]
        OpenRouter["OpenRouter LLM (Gemini 2.0 Flash / LLaMA 3.3)"]
    end

    subgraph Persistence["Storage & Database Tier"]
        MySQL[("MySQL 8.0 Database (Openings, Slots, Sessions, Messages)")]
        Cloudinary[("Cloudinary Asset Cloud (PDF & DOCX Resumes)")]
        AuditLogs[("Identity Audit Logs (identity_log_*.json)")]
    end

    CandidateUI -->|Webcam Frame| BioCtrl
    CandidateUI -->|Spoken Response| AgentCtrl
    RecruiterUI -->|Manage Openings & Review Shortlists| OpeningCtrl
    RecruiterUI -->|Inspect Final Recommendations & Turn Logs| FinalRankCtrl

    BioCtrl --> YuNet
    YuNet --> SFace
    SFace --> CosineMatch
    BioCtrl --> AuditLogs

    AgentCtrl --> LangGraphAgent
    LangGraphAgent --> OpenRouter

    OpeningCtrl --> Cloudinary
    ScheduleCtrl --> MySQL
    AgentCtrl --> MySQL
    FinalRankCtrl --> MySQL
```

---

## 2. End-to-End 5-Stage Pipeline Workflow

```mermaid
flowchart LR
    subgraph Stage1["Stage 1: Intake & Screening"]
        S1_Upload["Resume Upload (PDF / DOCX)"] --> S1_Parse["Dual-Engine Parser (pypdf & python-docx)"]
        S1_Parse --> S1_Eval["10-Competency LLM Evaluation"]
        S1_Eval --> S1_Rank["Screening Shortlist"]
    end

    subgraph Stage2["Stage 2: Scheduling"]
        S2_Slots["Slot Allocation Engine"] --> S2_Book["Atomic Slot Booking (Double-Booking Safe)"]
        S2_Book --> S2_Cal["Mock Calendar Confirmation (JSON)"]
    end

    subgraph Stage3["Stage 3: Identity Hard Gate"]
        S3_Cam["Live Webcam Capture"] --> S3_YuNet["YuNet Face Detection (0 / 1 / >1)"]
        S3_YuNet --> S3_SFace["SFace 128-D Embedding vs Reference Photo"]
        S3_SFace --> S3_Gate{"Cosine Sim >= 0.363?"}
        S3_Gate -- Yes --> S3_Pass["ALLOW_INTERVIEW"]
        S3_Gate -- No --> S3_Block["BLOCK & Route to Human Review"]
    end

    subgraph Stage4["Stage 4: Voice Interview"]
        S4_Start["Personalized Greeting & Opening Question"] --> S4_Candidate["Candidate Speaks (STT)"]
        S4_Candidate --> S4_Delib{"Deliberation Decision"}
        S4_Delib -- "narrow_follow_up" --> S4_Probe["Deep Probe Current Topic"]
        S4_Delib -- "broad_pivot" --> S4_Pivot["Pivot to Emergent Competency"]
        S4_Delib -- "next_competency" --> S4_Next["Advance Planned Topic"]
        S4_Delib -- "conclude" --> S4_End["Conclude Session"]
        S4_Probe --> S4_TTS["Audio Synthesis (TTS)"]
        S4_Pivot --> S4_TTS
        S4_Next --> S4_TTS
    end

    subgraph Stage5["Stage 5: Final Recommendation"]
        S5_Aggregate["Aggregate Turn Scores & Resume Scores"] --> S5_Formula["Composite Score = 0.40(Resume) + 0.60(Interview)"]
        S5_Formula --> S5_Cohort["Rank Cohort Descending (#1, #2, #3...)"]
        S5_Cohort --> S5_Report["Evidence Rationale & Turn Log Inspector"]
    end

    Stage1 --> Stage2
    Stage2 --> Stage3
    Stage3 --> Stage4
    Stage4 --> Stage5
```

---

## 3. The 10 Predefined Competencies Rubric

Every candidate is evaluated strictly against the following 10 competencies across Stage 1 (Resume) and Stage 4 (Interview):

1. **`technical_depth`:** Core software engineering fundamentals, low-level mechanics, algorithmic rigor, and language mastery.
2. **`system_architecture`:** Distributed systems design, microservices, scaling trade-offs, caching, and database internals.
3. **`problem_solving`:** Edge-case identification, debugging under pressure, root-cause diagnosis, and optimization.
4. **`communication`:** Clarity of thought, structured articulation, active listening, and technical storytelling.
5. **`leadership_mentorship`:** Guiding junior engineers, team leadership, architectural ownership, and knowledge sharing.
6. **`adaptability`:** Navigating unfamiliar technologies, pivoting priorities, and responding to changing production constraints.
7. **`domain_expertise`:** Specialized vertical knowledge (e.g. distributed streaming, machine learning pipelines, cloud infrastructure).
8. **`collaboration`:** Cross-functional partnership, code review etiquette, consensus building, and team alignment.
9. **`analytical_reasoning`:** Data-informed decision making, trade-off quantification, and metric-driven architecture.
10. **`delivery_reliability`:** Production ownership, CI/CD, comprehensive testing rigor, zero-downtime operations, and SLAs.

---

## 4. LangGraph Reasoning Agent State Machine

The reasoning agent maintains an immutable conversational state (`InterviewState`) progressing through the following nodes:

```mermaid
stateDiagram-v2
    [*] --> IngestContextNode
    IngestContextNode --> PlanAgendaNode
    PlanAgendaNode --> GenerateQuestionNode
    GenerateQuestionNode --> AwaitingCandidateResponse
    AwaitingCandidateResponse --> PerceiveEvaluateNode: Candidate Responds (Audio/Text)
    
    state PerceiveEvaluateNode {
        [*] --> SemanticAnalysis
        SemanticAnalysis --> CheckEmergentTopics
        CheckEmergentTopics --> DecisionPolicy
    }

    PerceiveEvaluateNode --> GenerateQuestionNode: Decision == narrow_follow_up
    PerceiveEvaluateNode --> GenerateQuestionNode: Decision == broad_pivot (New Competency)
    PerceiveEvaluateNode --> GenerateQuestionNode: Decision == next_competency
    PerceiveEvaluateNode --> FinalizeReportNode: Decision == conclude (Turns exhausted or agenda complete)
    FinalizeReportNode --> [*]
```

### Turn Reasoning Audit Record Format
For every interaction turn, the agent computes and logs:
```json
{
  "question_num": 2,
  "decision": "broad_pivot",
  "trigger_phrase_from_candidate": "When mentoring junior developers",
  "reasoning": "The candidate shifted from technical caching details to explain how they structured mentorship and code reviews for junior engineers. This surfaces the unassessed leadership_mentorship competency.",
  "question_asked": "Can you describe a specific instance where you mentored a junior engineer through a complex technical problem, and how you balanced guidance with fostering their independent problem-solving skills?",
  "score": 75.0,
  "competency_assessed": "leadership_mentorship"
}
```

---

## 5. Biometric Identity Verification & Hard Gate Architecture

The identity verification pipeline uses deep neural networks running directly inside OpenCV via ONNX runtime:

1. **Face Detection & Alignment:** **YuNet** (`face_detection_yunet_2023mar.onnx`) detects faces and identifies 5 landmark points (eyes, nose, mouth corners).
2. **Face Crop & Affine Normalization:** Cropped and affine-aligned to standard $112 \times 112$ pixels.
3. **Deep Face Embedding:** **SFace** (`face_recognition_sface_2021dec.onnx`) extracts an L2-normalized 128-dimensional embedding vector $\mathbf{v} \in \mathbb{R}^{128}$.
4. **Cosine Similarity Calculation:**
   $$\text{cosine\_similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
5. **Decision Policy:**
   - $\text{cosine} \ge 0.363 \implies \mathbf{PASS}$ (Confidence: $0.65 - 1.00$) $\implies$ `ALLOW_INTERVIEW`
   - $0.25 \le \text{cosine} < 0.363 \implies \mathbf{UNCERTAIN}$ (Confidence: $0.50 - 0.64$) $\implies$ `BLOCK_AND_ROUTE_TO_HUMAN_REVIEW`
   - $\text{cosine} < 0.25 \implies \mathbf{FAIL}$ (Confidence: $< 0.50$) $\implies$ `BLOCK_AND_ROUTE_TO_HUMAN_REVIEW`
   - Zero faces or $> 1$ face $\implies \mathbf{FAIL}$ $\implies$ `BLOCK_AND_ROUTE_TO_HUMAN_REVIEW`

---

## 6. Scoring & Cohort Ranking Formulations

$$\text{Composite Score} = (S_{\text{resume}} \times 0.40) + (S_{\text{interview}} \times 0.60)$$

Where:
- $S_{\text{resume}} \in [0, 100]$: Stage 1 score computed across the 10 predefined competencies based on resume evidence.
- $S_{\text{interview}} \in [0, 100]$: Stage 4 score computed as the weighted arithmetic mean of evaluated interview turns.
- **Hiring Recommendations:**
  - $\text{Composite} \ge 70.0 \implies \mathbf{RECOMMENDED}$
  - $55.0 \le \text{Composite} < 70.0 \implies \mathbf{BORDERLINE}$
  - $\text{Composite} < 55.0 \implies \mathbf{REJECTED}$

