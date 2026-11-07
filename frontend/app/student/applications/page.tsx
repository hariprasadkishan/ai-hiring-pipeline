"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApplicationItem {
  application_id: string;
  opening_id: string;
  title: string;
  program_type: "MTech" | "PhD";
  department: string;
  gpa: number;
  gate_score: number | null;
  resume_url: string | null;
  status:
    | "APPLIED"
    | "SHORTLISTED"
    | "REJECTED"
    | "INTERVIEW_PENDING"
    | "ACCEPTED"
    | "COMPLETED";
  resume_score: number | null;
  resume_feedback: {
    summary_reasoning?: string;
    matching_skills?: string[];
    missing_skills?: string[];
  } | null;
  applied_at: string;
}

export default function StudentApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const fetchMyApplications = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/applications/student/my-applications`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          router.push("/login");
          return;
        }
        throw new Error("Failed to load your applications.");
      }

      const data = await res.json();
      setApplications(data);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    let active = true;
    const init = async () => {
      if (active) await fetchMyApplications();
    };
    init();
    return () => {
      active = false;
    };
  }, [fetchMyApplications]);

  const getStatusBadgeStyle = (status: ApplicationItem["status"]) => {
    switch (status) {
      case "SHORTLISTED":
      case "ACCEPTED":
        return {
          backgroundColor: "#065f46",
          color: "#34d399",
          border: "1px solid #059669",
        };
      case "REJECTED":
        return {
          backgroundColor: "#881337",
          color: "#f43f5e",
          border: "1px solid #be123c",
        };
      case "INTERVIEW_PENDING":
        return {
          backgroundColor: "#78350f",
          color: "#fbbf24",
          border: "1px solid #d97706",
        };
      case "COMPLETED":
        return {
          backgroundColor: "#334155",
          color: "#cbd5e1",
          border: "1px solid #475569",
        };
      case "APPLIED":
      default:
        return {
          backgroundColor: "#1e3a8a",
          color: "#60a5fa",
          border: "1px solid #2563eb",
        };
    }
  };

  const getStatusDescription = (status: ApplicationItem["status"]) => {
    switch (status) {
      case "SHORTLISTED":
        return "Congratulations! Your application has been shortlisted. You are eligible to start your AI technical interview.";
      case "REJECTED":
        return "Your application was not selected for this position.";
      case "INTERVIEW_PENDING":
        return "You have an active or pending interview round ready to complete.";
      case "ACCEPTED":
        return "Congratulations! Offer extended for admission.";
      case "COMPLETED":
        return "Admission evaluation process finalized.";
      case "APPLIED":
      default:
        return "Application submitted and under academic review.";
    }
  };

  return (
    <div
      className="dashboard-container"
      style={{ maxWidth: "1000px", margin: "0 auto", padding: "2rem 1rem" }}
    >
      <header className="dashboard-header" style={{ marginBottom: "2rem" }}>
        <div>
          <h1 className="dashboard-title">My Applications</h1>
          <p className="dashboard-subtitle">
            Track evaluation status, feedback, and take your AI technical
            interview
          </p>
        </div>
      </header>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: "1.5rem" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div
          className="loading-state"
          style={{ textAlign: "center", padding: "3rem" }}
        >
          <div className="spinner-large" />
          <p style={{ marginTop: "1rem", color: "#94a3b8" }}>
            Loading your application status...
          </p>
        </div>
      ) : applications.length === 0 ? (
        <div
          className="empty-state"
          style={{
            textAlign: "center",
            padding: "3rem",
            backgroundColor: "#1e293b",
            borderRadius: "8px",
          }}
        >
          <h3 style={{ color: "#f8fafc" }}>No Applications Submitted Yet</h3>
          <p style={{ color: "#94a3b8", marginBottom: "1.5rem" }}>
            Browse open M.Tech and Ph.D. positions and submit your application.
          </p>
          <button
            onClick={() => router.push("/student/openings")}
            className="btn btn-primary"
          >
            Explore Openings
          </button>
        </div>
      ) : (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
        >
          {applications.map((app) => {
            const isInterviewEligible =
              app.status === "SHORTLISTED" ||
              app.status === "INTERVIEW_PENDING";

            return (
              <div
                key={app.application_id}
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  padding: "1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "1rem",
                }}
              >
                {/* Header Row */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "0.25rem",
                      }}
                    >
                      <span
                        className={`badge badge-degree ${app.program_type.toLowerCase()}`}
                      >
                        {app.program_type}
                      </span>
                      <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                        {app.department}
                      </span>
                    </div>
                    <h2
                      style={{
                        margin: 0,
                        fontSize: "1.25rem",
                        color: "#f8fafc",
                      }}
                    >
                      {app.title}
                    </h2>
                  </div>

                  <span
                    style={{
                      padding: "0.35rem 0.75rem",
                      borderRadius: "9999px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      ...getStatusBadgeStyle(app.status),
                    }}
                  >
                    {app.status.replace("_", " ")}
                  </span>
                </div>

                {/* Status Explanation Banner */}
                <div
                  style={{
                    backgroundColor: "#0f172a",
                    padding: "0.75rem 1rem",
                    borderRadius: "6px",
                    borderLeft: `4px solid ${isInterviewEligible ? "#10b981" : "#3b82f6"}`,
                    fontSize: "0.875rem",
                    color: "#e2e8f0",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "0.75rem",
                  }}
                >
                  <span>{getStatusDescription(app.status)}</span>

                  {/* AI Interview Launch Button */}
                  {isInterviewEligible && (
                    <button
                      onClick={() =>
                        router.push(`/student/interview/${app.application_id}`)
                      }
                      style={{
                        backgroundColor: "#10b981",
                        color: "#022c22",
                        border: "none",
                        padding: "0.5rem 1.25rem",
                        borderRadius: "6px",
                        fontWeight: 700,
                        cursor: "pointer",
                        fontSize: "0.875rem",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        boxShadow: "0 2px 8px rgba(16, 185, 129, 0.3)",
                      }}
                    >
                      <span>🤖</span> Start AI Interview
                    </button>
                  )}
                </div>

                {/* Application Details Grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "1rem",
                    paddingTop: "0.5rem",
                    borderTop: "1px solid #334155",
                    fontSize: "0.85rem",
                    color: "#94a3b8",
                  }}
                >
                  <div>
                    Submitted GPA:{" "}
                    <strong style={{ color: "#f8fafc" }}>{app.gpa} / 10</strong>
                  </div>
                  <div>
                    GATE Score:{" "}
                    <strong style={{ color: "#f8fafc" }}>
                      {app.gate_score ?? "N/A"}
                    </strong>
                  </div>
                  <div>
                    Applied On:{" "}
                    <strong style={{ color: "#f8fafc" }}>
                      {new Date(app.applied_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </strong>
                  </div>
                  {app.resume_url && (
                    <div>
                      Submitted Resume:{" "}
                      <a
                        href={`${API_BASE_URL}/api/applications/${app.application_id}/resume?token=${localStorage.getItem(
                          "access_token",
                        )}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: "#60a5fa",
                          textDecoration: "underline",
                          marginLeft: "0.25rem",
                        }}
                      >
                        View PDF
                      </a>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
