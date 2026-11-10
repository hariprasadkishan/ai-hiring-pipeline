"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CompetencyItem {
  score: number;
  evidence: string;
  analysis: string;
}

interface Applicant {
  application_id: string;
  student_name: string;
  student_email: string;
  gpa: number;
  gate_score: number | null;
  resume_url: string | null;
  resume_score: number | null;
  resume_feedback: {
    summary_reasoning?: string;
    matching_skills?: string[];
    missing_skills?: string[];
    competencies?: Record<string, CompetencyItem>;
    extracted_profile?: {
      candidate_name?: string;
      contact_email?: string;
      contact_phone?: string;
      education?: string[];
      skills?: string[];
      experience_summary?: string;
    };
  } | null;
  status:
    | "APPLIED"
    | "SHORTLISTED"
    | "REJECTED"
    | "INTERVIEW_PENDING"
    | "ACCEPTED"
    | "COMPLETED";
  applied_at: string;
}

interface OpeningDetails {
  opening_id: string;
  title: string;
  program_type: "MTech" | "PhD";
  min_gpa: number;
  min_gate_score: number | null;
  status: string;
}

interface TurnReasoningItem {
  question_num: number;
  competency?: string;
  decision?: string;
  trigger_phrase_from_candidate?: string;
  reasoning?: string;
  question_asked?: string;
  score?: number;
}

interface FinalRecommendationCandidate {
  rank: number;
  application_id: string;
  student_id: string;
  candidate_name: string;
  candidate_email: string;
  gpa: number;
  resume_score: number;
  interview_score?: number | null;
  composite_score: number;
  status: string;
  recommendation: string;
  competency_scores: Record<string, number>;
  verdict_rationale: string;
  evidence_summary?: any;
  turn_reasoning_logs: TurnReasoningItem[];
}

interface FinalRecommendationReport {
  opening_id: string;
  opening_title: string;
  total_candidates: number;
  completed_interviews: number;
  ranked_candidates: FinalRecommendationCandidate[];
}

export default function FacultyApplicantsPage() {
  const params = useParams();
  const router = useRouter();
  const openingId = params.opening_id as string;

  // Active Stage Tab
  const [activeTab, setActiveTab] = useState<"stage1" | "stage5">("stage1");

  const [opening, setOpening] = useState<OpeningDetails | null>(null);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [positionsAvailable, setPositionsAvailable] = useState<string>("3");
  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  // Modals
  const [detailModalApplicant, setDetailModalApplicant] = useState<Applicant | null>(null);
  const [reasoningModalCandidate, setReasoningModalCandidate] = useState<FinalRecommendationCandidate | null>(null);

  // Stage 5 Cohort Report
  const [finalReport, setFinalReport] = useState<FinalRecommendationReport | null>(null);
  const [loadingFinalReport, setLoadingFinalReport] = useState<boolean>(false);

  const fetchApplicants = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/");
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/openings/${openingId}/applicants`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          router.push("/");
          return;
        }
        throw new Error("Failed to load applicants.");
      }

      const data = await res.json();
      setOpening(data.opening);
      setApplicants(data.applicants);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [openingId, router]);

  const fetchFinalRecommendations = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    setLoadingFinalReport(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/interview/final-recommendations/${openingId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (res.ok) {
        const data = await res.json();
        setFinalReport(data);
      }
    } catch (e) {
      console.warn("Could not fetch final recommendations:", e);
    } finally {
      setLoadingFinalReport(false);
    }
  }, [openingId]);

  useEffect(() => {
    let active = true;
    const initializeData = async () => {
      if (active) {
        await fetchApplicants();
        await fetchFinalRecommendations();
      }
    };
    initializeData();
    return () => {
      active = false;
    };
  }, [fetchApplicants, fetchFinalRecommendations]);

  const handleRunEvaluation = async () => {
    const capacity = parseInt(positionsAvailable, 10);
    if (isNaN(capacity) || capacity <= 0) {
      alert("Please enter a valid number of positions available.");
      return;
    }

    if (!confirm(`Run academic filtering and shortlist top ${capacity} candidates?`)) {
      return;
    }

    setEvaluating(true);
    setError("");
    const token = localStorage.getItem("access_token");

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/openings/${openingId}/evaluate-resumes`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ positions_available: capacity, force_reevaluate: true }),
        },
      );

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Evaluation failed.");

      alert(`Evaluation complete across 10 predefined competencies!`);
      await fetchApplicants();
      await fetchFinalRecommendations();
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="dashboard-container">
      {opening && (
        <header className="dashboard-header">
          <div>
            <span className={`badge badge-degree ${opening.program_type.toLowerCase()}`}>
              {opening.program_type}
            </span>
            <h1 className="dashboard-title" style={{ marginTop: "0.25rem" }}>
              {opening.title}
            </h1>
            <p className="dashboard-subtitle">
              End-to-End AI Hiring Pipeline: Resume Screening, Biometric Gate, Voice Reasoning & Cohort Ranking
            </p>
          </div>

          {/* Action Box */}
          <div
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              padding: "0.85rem 1.25rem",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block" }}>
                Positions to Fill:
              </label>
              <input
                type="number"
                min="1"
                className="form-input-dark"
                style={{ width: "80px", padding: "0.35rem 0.5rem", fontSize: "0.85rem" }}
                value={positionsAvailable}
                onChange={(e) => setPositionsAvailable(e.target.value)}
              />
            </div>

            <button
              onClick={handleRunEvaluation}
              disabled={evaluating || applicants.length === 0}
              className="btn btn-primary"
              style={{ alignSelf: "flex-end", padding: "0.5rem 1rem", fontSize: "0.85rem" }}
            >
              {evaluating ? "Scoring 10 Competencies..." : "Score Resumes (10 Competencies)"}
            </button>
          </div>
        </header>
      )}

      {/* Pipeline Stage Tab Switcher */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          borderBottom: "1px solid #334155",
          paddingBottom: "0.75rem",
          marginBottom: "1.5rem",
        }}
      >
        <button
          onClick={() => setActiveTab("stage1")}
          style={{
            backgroundColor: activeTab === "stage1" ? "#2563eb" : "#1e293b",
            color: activeTab === "stage1" ? "#ffffff" : "#94a3b8",
            border: `1px solid ${activeTab === "stage1" ? "#3b82f6" : "#334155"}`,
            padding: "0.55rem 1.25rem",
            borderRadius: "6px",
            fontSize: "0.85rem",
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
          }}
        >
          📄 Stage 1: Resume Intake & 10 Competencies ({applicants.length})
        </button>

        <button
          onClick={() => {
            setActiveTab("stage5");
            fetchFinalRecommendations();
          }}
          style={{
            backgroundColor: activeTab === "stage5" ? "#7c3aed" : "#1e293b",
            color: activeTab === "stage5" ? "#ffffff" : "#94a3b8",
            border: `1px solid ${activeTab === "stage5" ? "#8b5cf6" : "#334155"}`,
            padding: "0.55rem 1.25rem",
            borderRadius: "6px",
            fontSize: "0.85rem",
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
          }}
        >
          🏆 Stage 5: Final Recommendations & Ranked Shortlist ({finalReport?.completed_interviews || 0} Finished)
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* TAB 1: STAGE 1 RESUME SCREENING & 10 COMPETENCIES                   */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === "stage1" && (
        <>
          {loading ? (
            <div className="loading-state">
              <div className="spinner-large" />
              <p>Fetching candidate submissions...</p>
            </div>
          ) : applicants.length === 0 ? (
            <div className="empty-state">
              <h3>No Applicants Found</h3>
              <p>No candidates have applied for this position yet.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {applicants.map((app) => (
                <div
                  key={app.application_id}
                  className="opening-card-dash"
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "1rem",
                  }}
                >
                  <div style={{ flex: 2, minWidth: "260px" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.75rem",
                        marginBottom: "0.4rem",
                      }}
                    >
                      <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{app.student_name}</h3>
                      <span className={`badge badge-status status-${app.status.toLowerCase()}`}>
                        {app.status}
                      </span>
                    </div>
                    <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.85rem" }}>
                      {app.student_email}
                    </p>

                    <div
                      style={{
                        display: "flex",
                        gap: "1.5rem",
                        marginTop: "0.75rem",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span>
                        GPA: <strong>{app.gpa} / 10</strong>
                      </span>
                      <span>
                        GATE: <strong>{app.gate_score ?? "N/A"}</strong>
                      </span>
                      {app.resume_url && (
                        <a
                          href={`${API_BASE_URL}/api/applications/${app.application_id}/resume?token=${localStorage.getItem("access_token")}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "#60a5fa", textDecoration: "underline" }}
                        >
                          View Resume Document
                        </a>
                      )}
                    </div>
                  </div>

                  {/* AI Evaluation Output */}
                  <div
                    style={{
                      flex: 3,
                      minWidth: "300px",
                      backgroundColor: "#0f172a",
                      padding: "0.85rem",
                      borderRadius: "6px",
                      border: "1px solid #334155",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "0.4rem",
                      }}
                    >
                      <span style={{ fontSize: "0.8rem", color: "#60a5fa", fontWeight: 600 }}>
                        Stage 1 Evidence Score
                      </span>
                      <strong
                        style={{
                          fontSize: "1rem",
                          color:
                            app.resume_score && app.resume_score >= 70
                              ? "#34d399"
                              : "#f59e0b",
                        }}
                      >
                        {app.resume_score !== null ? `${app.resume_score} / 100` : "Not Evaluated"}
                      </strong>
                    </div>

                    <p style={{ fontSize: "0.82rem", color: "#cbd5e1", margin: 0, lineHeight: "1.4" }}>
                      {app.resume_feedback?.summary_reasoning || "Awaiting evaluation execution."}
                    </p>

                    {/* Button to view 10 competencies modal */}
                    {app.resume_feedback?.competencies && (
                      <div style={{ marginTop: "0.6rem" }}>
                        <button
                          onClick={() => setDetailModalApplicant(app)}
                          style={{
                            backgroundColor: "#1e3a8a",
                            color: "#93c5fd",
                            border: "1px solid #3b82f6",
                            padding: "0.3rem 0.65rem",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          🔍 View 10-Competency Evidence Breakdown →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* TAB 2: STAGE 5 FINAL RECOMMENDATIONS & RANKED SHORTLIST             */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === "stage5" && (
        <div>
          {loadingFinalReport ? (
            <div className="loading-state">
              <div className="spinner-large" />
              <p>Aggregating candidate multi-stage scores & cohort rankings...</p>
            </div>
          ) : !finalReport || finalReport.ranked_candidates.length === 0 ? (
            <div className="empty-state">
              <h3>No Evaluated Candidates Yet</h3>
              <p>Execute Stage 1 resume scoring and conduct interviews to populate final rankings.</p>
            </div>
          ) : (
            <div>
              {/* Cohort Overview Bar */}
              <div
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #475569",
                  borderRadius: "8px",
                  padding: "1rem 1.5rem",
                  marginBottom: "1.5rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "1rem",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Cohort Sizing</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
                    {finalReport.total_candidates} Applicants • {finalReport.completed_interviews} Completed Interviews
                  </div>
                </div>

                <div style={{ display: "flex", gap: "1rem" }}>
                  <div style={{ textAlign: "center", backgroundColor: "#0f172a", padding: "0.5rem 1rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Formula</div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#38bdf8" }}>
                      40% Resume + 60% Voice Interview
                    </div>
                  </div>
                  <div style={{ textAlign: "center", backgroundColor: "#0f172a", padding: "0.5rem 1rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Top Candidate</div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#10b981" }}>
                      {finalReport.ranked_candidates[0]?.candidate_name || "N/A"} ({finalReport.ranked_candidates[0]?.composite_score}/100)
                    </div>
                  </div>
                </div>
              </div>

              {/* Ranked Candidates Cards */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {finalReport.ranked_candidates.map((cand) => (
                  <div
                    key={cand.application_id}
                    style={{
                      backgroundColor: "#1e293b",
                      border: `2px solid ${
                        cand.recommendation === "RECOMMENDED"
                          ? "#10b981"
                          : cand.recommendation === "BORDERLINE"
                          ? "#f59e0b"
                          : cand.recommendation === "REJECTED"
                          ? "#ef4444"
                          : "#475569"
                      }`,
                      borderRadius: "10px",
                      padding: "1.25rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.85rem",
                    }}
                  >
                    {/* Header Row: Rank, Name, Recommendation Badge, Composite Score */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <span
                          style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "50%",
                            backgroundColor: cand.rank === 1 ? "#eab308" : cand.rank === 2 ? "#94a3b8" : "#475569",
                            color: cand.rank === 1 ? "#0f172a" : "#f8fafc",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 800,
                            fontSize: "1rem",
                          }}
                        >
                          #{cand.rank}
                        </span>
                        <div>
                          <h3 style={{ margin: 0, fontSize: "1.15rem", color: "#f8fafc", fontWeight: 700 }}>
                            {cand.candidate_name}
                          </h3>
                          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                            {cand.candidate_email} • GPA: {cand.gpa}/10
                          </span>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                        {/* Recommendation Badge */}
                        <span
                          style={{
                            backgroundColor:
                              cand.recommendation === "RECOMMENDED"
                                ? "#065f46"
                                : cand.recommendation === "BORDERLINE"
                                ? "#78350f"
                                : cand.recommendation === "REJECTED"
                                ? "#881337"
                                : "#334155",
                            color:
                              cand.recommendation === "RECOMMENDED"
                                ? "#34d399"
                                : cand.recommendation === "BORDERLINE"
                                ? "#fbbf24"
                                : cand.recommendation === "REJECTED"
                                ? "#f43f5e"
                                : "#94a3b8",
                            padding: "0.35rem 0.85rem",
                            borderRadius: "9999px",
                            fontSize: "0.8rem",
                            fontWeight: 800,
                          }}
                        >
                          {cand.recommendation.replace("_", " ")}
                        </span>

                        {/* Composite Score Pill */}
                        <div
                          style={{
                            backgroundColor: "#0f172a",
                            border: "1px solid #334155",
                            borderRadius: "6px",
                            padding: "0.35rem 0.75rem",
                            textAlign: "right",
                          }}
                        >
                          <div style={{ fontSize: "0.7rem", color: "#94a3b8" }}>Composite Score</div>
                          <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#38bdf8" }}>
                            {cand.composite_score} / 100
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Breakdown Scores Row */}
                    <div
                      style={{
                        display: "flex",
                        gap: "1.5rem",
                        backgroundColor: "#0f172a",
                        padding: "0.6rem 1rem",
                        borderRadius: "6px",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span>
                        Stage 1 Resume Score (40%): <strong>{cand.resume_score}</strong>
                      </span>
                      <span>
                        Stage 4 Voice Interview Score (60%):{" "}
                        <strong>{cand.interview_score !== null ? cand.interview_score : "Pending"}</strong>
                      </span>
                    </div>

                    {/* Verdict Rationale */}
                    <p style={{ margin: 0, fontSize: "0.85rem", color: "#cbd5e1", lineHeight: 1.5 }}>
                      <strong>AI Committee Verdict:</strong> {cand.verdict_rationale}
                    </p>

                    {/* 10 Predefined Competencies Score Bar Grid */}
                    {cand.competency_scores && Object.keys(cand.competency_scores).length > 0 && (
                      <div>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "0.35rem" }}>
                          10 Predefined Competencies Distribution:
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                            gap: "0.4rem",
                          }}
                        >
                          {Object.entries(cand.competency_scores).map(([compName, score]) => (
                            <div
                              key={compName}
                              style={{
                                backgroundColor: "#0f172a",
                                border: "1px solid #334155",
                                borderRadius: "4px",
                                padding: "0.3rem 0.5rem",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                fontSize: "0.75rem",
                              }}
                            >
                              <span style={{ color: "#cbd5e1", textTransform: "capitalize" }}>
                                {compName.replace(/_/g, " ")}
                              </span>
                              <span
                                style={{
                                  fontWeight: 700,
                                  color: score >= 75 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f43f5e",
                                }}
                              >
                                {score}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Bar */}
                    <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.25rem" }}>
                      {cand.turn_reasoning_logs && cand.turn_reasoning_logs.length > 0 && (
                        <button
                          onClick={() => setReasoningModalCandidate(cand)}
                          style={{
                            backgroundColor: "#312e81",
                            color: "#c7d2fe",
                            border: "1px solid #4338ca",
                            padding: "0.4rem 0.85rem",
                            borderRadius: "4px",
                            fontSize: "0.8rem",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          🧠 Inspect Turn Reasoning Logs ({cand.turn_reasoning_logs.length} Turns) →
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 1: 10-COMPETENCY RESUME EVIDENCE MODAL (STAGE 1)              */}
      {/* ------------------------------------------------------------------ */}
      {detailModalApplicant && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <div
            style={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              maxWidth: "750px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "1.5rem",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
                borderBottom: "1px solid #334155",
                paddingBottom: "0.75rem",
              }}
            >
              <div>
                <h3 style={{ margin: 0, color: "#f8fafc", fontSize: "1.2rem" }}>
                  10-Competency Evidence Evaluation
                </h3>
                <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.85rem" }}>
                  {detailModalApplicant.student_name} • Match Score: {detailModalApplicant.resume_score}/100
                </p>
              </div>
              <button
                onClick={() => setDetailModalApplicant(null)}
                style={{
                  backgroundColor: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {/* Candidate Extracted Profile */}
            {detailModalApplicant.resume_feedback?.extracted_profile && (
              <div
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  padding: "0.75rem",
                  marginBottom: "1rem",
                  fontSize: "0.85rem",
                }}
              >
                <div style={{ color: "#60a5fa", fontWeight: 700, marginBottom: "0.25rem" }}>
                  Extracted Candidate Profile
                </div>
                <div style={{ color: "#cbd5e1" }}>
                  {detailModalApplicant.resume_feedback.extracted_profile.education?.length ? (
                    <div>Education: {detailModalApplicant.resume_feedback.extracted_profile.education.join(" • ")}</div>
                  ) : null}
                  {detailModalApplicant.resume_feedback.extracted_profile.skills?.length ? (
                    <div style={{ marginTop: "0.25rem" }}>
                      Skills: {detailModalApplicant.resume_feedback.extracted_profile.skills.slice(0, 10).join(", ")}
                    </div>
                  ) : null}
                </div>
              </div>
            )}

            {/* 10 Predefined Competencies Grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {detailModalApplicant.resume_feedback?.competencies &&
                Object.entries(detailModalApplicant.resume_feedback.competencies).map(([key, comp]) => (
                  <div
                    key={key}
                    style={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "0.75rem",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "0.35rem",
                      }}
                    >
                      <span style={{ fontWeight: 700, color: "#f8fafc", textTransform: "capitalize", fontSize: "0.9rem" }}>
                        {key.replace(/_/g, " ")}
                      </span>
                      <span
                        style={{
                          fontWeight: 800,
                          fontSize: "0.9rem",
                          color: comp.score >= 7.5 ? "#34d399" : comp.score >= 5 ? "#fbbf24" : "#f43f5e",
                        }}
                      >
                        {comp.score} / 10
                      </span>
                    </div>

                    <p style={{ margin: "0 0 0.35rem 0", fontSize: "0.82rem", color: "#cbd5e1" }}>
                      {comp.analysis}
                    </p>

                    <div
                      style={{
                        backgroundColor: "#020617",
                        padding: "0.4rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.78rem",
                        color: "#94a3b8",
                        fontStyle: "italic",
                        borderLeft: "3px solid #38bdf8",
                      }}
                    >
                      Evidence: &ldquo;{comp.evidence}&rdquo;
                    </div>
                  </div>
                ))}
            </div>

            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <button
                onClick={() => setDetailModalApplicant(null)}
                className="btn btn-primary"
                style={{ padding: "0.4rem 1rem", fontSize: "0.85rem" }}
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 2: TURN-BY-TURN REASONING LOGS MODAL (STAGE 4 & 5)           */}
      {/* ------------------------------------------------------------------ */}
      {reasoningModalCandidate && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <div
            style={{
              backgroundColor: "#0f172a",
              border: "1px solid #4338ca",
              borderRadius: "10px",
              maxWidth: "800px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "1.5rem",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
                borderBottom: "1px solid #334155",
                paddingBottom: "0.75rem",
              }}
            >
              <div>
                <h3 style={{ margin: 0, color: "#f8fafc", fontSize: "1.2rem", fontWeight: 700 }}>
                  🧠 Stage 4 Voice Turn Reasoning Logs
                </h3>
                <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.85rem" }}>
                  Candidate: {reasoningModalCandidate.candidate_name} • Audit Trail of Semantic Pivots & Probes
                </p>
              </div>
              <button
                onClick={() => setReasoningModalCandidate(null)}
                style={{
                  backgroundColor: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {reasoningModalCandidate.turn_reasoning_logs.map((log, index) => (
                <div
                  key={index}
                  style={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "1rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "0.5rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span
                        style={{
                          backgroundColor: "#334155",
                          color: "#f8fafc",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: 700,
                        }}
                      >
                        Turn {log.question_num}
                      </span>
                      <span
                        style={{
                          backgroundColor:
                            log.decision === "broad_pivot"
                              ? "#581c87"
                              : log.decision === "narrow_follow_up"
                              ? "#1e3a8a"
                              : "#064e3b",
                          color:
                            log.decision === "broad_pivot"
                              ? "#d8b4fe"
                              : log.decision === "narrow_follow_up"
                              ? "#93c5fd"
                              : "#6ee7b7",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: 800,
                        }}
                      >
                        {log.decision?.toUpperCase().replace("_", " ")}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "capitalize" }}>
                        ({log.competency?.replace(/_/g, " ")})
                      </span>
                    </div>

                    {log.score !== undefined && (
                      <span style={{ fontWeight: 700, color: "#38bdf8", fontSize: "0.85rem" }}>
                        Score: {log.score}/100
                      </span>
                    )}
                  </div>

                  {log.trigger_phrase_from_candidate && (
                    <div
                      style={{
                        backgroundColor: "#020617",
                        borderLeft: "3px solid #f59e0b",
                        padding: "0.4rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        color: "#fde68a",
                        marginBottom: "0.5rem",
                        fontStyle: "italic",
                      }}
                    >
                      Candidate Trigger Phrase: &ldquo;{log.trigger_phrase_from_candidate}&rdquo;
                    </div>
                  )}

                  <div style={{ fontSize: "0.82rem", color: "#cbd5e1", marginBottom: "0.5rem", lineHeight: 1.5 }}>
                    <strong>AI Deliberation Reasoning:</strong> {log.reasoning}
                  </div>

                  {log.question_asked && (
                    <div
                      style={{
                        backgroundColor: "#0f172a",
                        padding: "0.5rem 0.75rem",
                        borderRadius: "4px",
                        fontSize: "0.82rem",
                        color: "#38bdf8",
                        border: "1px solid #1e3a8a",
                      }}
                    >
                      <strong>Question Formulated:</strong> &ldquo;{log.question_asked}&rdquo;
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <button
                onClick={() => setReasoningModalCandidate(null)}
                className="btn btn-primary"
                style={{ padding: "0.4rem 1rem", fontSize: "0.85rem" }}
              >
                Close Audit Logs
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
