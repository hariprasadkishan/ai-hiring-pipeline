"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export default function FacultyApplicantsPage() {
  const params = useParams();
  const router = useRouter();
  const openingId = params.opening_id as string;

  const [opening, setOpening] = useState<OpeningDetails | null>(null);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [positionsAvailable, setPositionsAvailable] = useState<string>("3");
  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const fetchApplicants = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
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
          router.push("/login");
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

  // FIX: Isolated initialization task executed within a dedicated asynchronous wrapper context
  useEffect(() => {
    let active = true;

    const initializeData = async () => {
      if (active) {
        await fetchApplicants();
      }
    };

    initializeData();

    return () => {
      active = false;
    };
  }, [fetchApplicants]);

  const handleRunEvaluation = async () => {
    const capacity = parseInt(positionsAvailable, 10);
    if (isNaN(capacity) || capacity <= 0) {
      alert("Please enter a valid number of positions available.");
      return;
    }

    if (
      !confirm(
        `Run academic filtering and shortlist top ${capacity} candidates?`,
      )
    ) {
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
          body: JSON.stringify({ positions_available: capacity }),
        },
      );

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Evaluation failed.");

      alert(`Evaluation complete! Shortlisted ${data.shortlisted} candidates.`);
      fetchApplicants();
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
            <span
              className={`badge badge-degree ${opening.program_type.toLowerCase()}`}
            >
              {opening.program_type}
            </span>
            <h1 className="dashboard-title" style={{ marginTop: "0.25rem" }}>
              {opening.title}
            </h1>
            <p className="dashboard-subtitle">
              Review Applicants & Execute AI Resume Evaluation
            </p>
          </div>

          {/* Evaluation Action Box */}
          <div
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              padding: "1rem",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <div>
              <label
                style={{
                  fontSize: "0.8rem",
                  color: "#94a3b8",
                  display: "block",
                }}
              >
                Positions Available:
              </label>
              <input
                type="number"
                min="1"
                className="form-input-dark"
                style={{ width: "90px", padding: "0.4rem 0.6rem" }}
                value={positionsAvailable}
                onChange={(e) => setPositionsAvailable(e.target.value)}
              />
            </div>

            <button
              onClick={handleRunEvaluation}
              disabled={evaluating || applicants.length === 0}
              className="btn btn-primary"
              style={{ alignSelf: "flex-end" }}
            >
              {evaluating
                ? "Evaluating Resumes..."
                : "Run AI Evaluation & Shortlist"}
            </button>
          </div>
        </header>
      )}

      {error && (
        <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

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
                  <h3 style={{ margin: 0, fontSize: "1.1rem" }}>
                    {app.student_name}
                  </h3>
                  <span
                    className={`badge badge-status status-${app.status.toLowerCase()}`}
                  >
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
                      View Resume PDF
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
                  <span
                    style={{
                      fontSize: "0.8rem",
                      color: "#60a5fa",
                      fontWeight: 600,
                    }}
                  >
                    AI Resume Match Score
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
                    {app.resume_score !== null
                      ? `${app.resume_score} / 100`
                      : "Not Evaluated"}
                  </strong>
                </div>

                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "#cbd5e1",
                    margin: 0,
                    lineHeight: "1.4",
                  }}
                >
                  {app.resume_feedback?.summary_reasoning ||
                    "Pending evaluation execution."}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
