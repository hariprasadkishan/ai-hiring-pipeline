"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Opening {
  opening_id: string;
  title: string;
  program_type: "MTech" | "PhD";
  department: string;
  description: string | null;
  research_areas: string[];
  preferred_skills: string[];
  min_gpa: number;
  min_gate_score: number | null;
  prerequisites: string[];
  syllabus_topics: string[];
  start_date: string;
  end_date: string;
  status: "UPCOMING" | "ACTIVE" | "CLOSED";
  has_applied: boolean;
}

export default function StudentOpeningsPage() {
  const router = useRouter();
  const [openings, setOpenings] = useState<Opening[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Modal States
  const [viewingOpening, setViewingOpening] = useState<Opening | null>(null); // JD Details Pop-out
  const [selectedOpening, setSelectedOpening] = useState<Opening | null>(null); // Apply Form Modal

  // Application Form State
  const [gpaInput, setGpaInput] = useState("");
  const [gateInput, setGateInput] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [applyError, setApplyError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchOpenings = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/openings/student`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          router.push("/login");
          return;
        }
        throw new Error("Failed to load admission openings.");
      }

      const data: Opening[] = await res.json();
      setOpenings(data);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    let active = true;

    const initFetch = async () => {
      if (active) {
        await fetchOpenings();
      }
    };

    initFetch();

    return () => {
      active = false;
    };
  }, [fetchOpenings]);

  const handleApplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOpening) return;

    if (selectedOpening.program_type === "PhD" && !resumeFile) {
      setApplyError(
        "Please select a PDF resume file to upload for Ph.D. application.",
      );
      return;
    }

    setApplyError("");
    setSubmitting(true);

    const token = localStorage.getItem("access_token");
    const formData = new FormData();
    formData.append("opening_id", selectedOpening.opening_id);
    formData.append("gpa", gpaInput);
    if (gateInput.trim()) formData.append("gate_score", gateInput);
    if (resumeFile) formData.append("resume", resumeFile);

    try {
      const res = await fetch(`${API_BASE_URL}/api/applications/apply`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();
      if (!res.ok)
        throw new Error(data.detail || "Application submission failed.");

      alert("Application submitted successfully!");
      setSelectedOpening(null);
      setGpaInput("");
      setGateInput("");
      setResumeFile(null);
      fetchOpenings();
    } catch (err: unknown) {
      if (err instanceof Error) setApplyError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Postgraduate Admission Openings</h1>
          <p className="dashboard-subtitle">
            Explore active M.Tech and Ph.D. positions and submit your
            application
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-state">
          <div className="spinner-large" />
          <p>Loading available positions...</p>
        </div>
      ) : openings.length === 0 ? (
        <div className="empty-state">
          <h3>No Openings Available</h3>
          <p>Check back later for new admission notifications.</p>
        </div>
      ) : (
        <div className="openings-grid">
          {openings.map((op) => (
            <div key={op.opening_id} className="opening-card-dash">
              <div className="opening-card-header">
                <span
                  className={`badge badge-degree ${op.program_type.toLowerCase()}`}
                >
                  {op.program_type === "MTech" ? "M.Tech" : "Ph.D."}
                </span>
                <span
                  className={`badge badge-status status-${op.status.toLowerCase()}`}
                >
                  {op.status}
                </span>
              </div>

              <h3 className="opening-card-title">{op.title}</h3>
              <p className="opening-card-dept">{op.department}</p>

              <div className="opening-details">
                <div>
                  <span>Min GPA:</span> <strong>{op.min_gpa} / 10</strong>
                </div>
                <div>
                  <span>Min GATE:</span>{" "}
                  <strong>{op.min_gate_score ?? "N/A"}</strong>
                </div>
              </div>

              {/* Action Buttons */}
              <div
                className="opening-card-footer"
                style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
              >
                <button
                  onClick={() => setViewingOpening(op)}
                  className="btn"
                  style={{
                    backgroundColor: "#334155",
                    color: "#f8fafc",
                    padding: "0.4rem 0.8rem",
                    fontSize: "0.85rem",
                  }}
                >
                  View JD
                </button>

                {op.has_applied ? (
                  <span className="badge status-active">Applied</span>
                ) : op.status === "ACTIVE" ? (
                  <button
                    onClick={() => {
                      setSelectedOpening(op);
                      setApplyError("");
                    }}
                    className="btn btn-primary"
                    style={{
                      padding: "0.4rem 1rem",
                      fontSize: "0.85rem",
                      marginLeft: "auto",
                    }}
                  >
                    Apply Now
                  </button>
                ) : (
                  <span
                    className="text-muted-val"
                    style={{ fontSize: "0.85rem", marginLeft: "auto" }}
                  >
                    Closed
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 1. Job Description (JD) Pop-Out Modal */}
      {viewingOpening && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            zIndex: 100,
          }}
        >
          <div
            className="opening-card"
            style={{ maxWidth: "600px", maxHeight: "85vh", overflowY: "auto" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "1rem",
              }}
            >
              <div>
                <span
                  className={`badge badge-degree ${viewingOpening.program_type.toLowerCase()}`}
                  style={{ marginBottom: "0.5rem", display: "inline-block" }}
                >
                  {viewingOpening.program_type === "MTech" ? "M.Tech" : "Ph.D."}
                </span>
                <h2
                  className="opening-title"
                  style={{ fontSize: "1.35rem", margin: 0 }}
                >
                  {viewingOpening.title}
                </h2>
                <p
                  style={{
                    color: "#94a3b8",
                    fontSize: "0.9rem",
                    marginTop: "0.25rem",
                  }}
                >
                  {viewingOpening.department}
                </p>
              </div>
            </div>

            {/* Description Section */}
            {viewingOpening.description ? (
              <div style={{ marginBottom: "1.25rem" }}>
                <h4
                  style={{
                    color: "#60a5fa",
                    fontSize: "0.95rem",
                    marginBottom: "0.4rem",
                  }}
                >
                  Project & Lab Scope
                </h4>
                <p
                  style={{
                    fontSize: "0.9rem",
                    color: "#cbd5e1",
                    lineHeight: "1.5",
                  }}
                >
                  {viewingOpening.description}
                </p>
              </div>
            ) : (
              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#94a3b8",
                  fontStyle: "italic",
                }}
              >
                No detailed narrative description provided for this opening.
              </p>
            )}

            {/* Research Areas */}
            {viewingOpening.research_areas &&
              viewingOpening.research_areas.length > 0 && (
                <div style={{ marginBottom: "1rem" }}>
                  <h4
                    style={{
                      color: "#60a5fa",
                      fontSize: "0.95rem",
                      marginBottom: "0.4rem",
                    }}
                  >
                    Target Research Areas
                  </h4>
                  <div
                    style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}
                  >
                    {viewingOpening.research_areas.map((area, idx) => (
                      <span
                        key={idx}
                        style={{
                          backgroundColor: "rgba(96, 165, 250, 0.15)",
                          color: "#93c5fd",
                          border: "1px solid rgba(96, 165, 250, 0.3)",
                          padding: "0.2rem 0.6rem",
                          borderRadius: "4px",
                          fontSize: "0.82rem",
                        }}
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            {/* Preferred Skills */}
            {viewingOpening.preferred_skills &&
              viewingOpening.preferred_skills.length > 0 && (
                <div style={{ marginBottom: "1rem" }}>
                  <h4
                    style={{
                      color: "#34d399",
                      fontSize: "0.95rem",
                      marginBottom: "0.4rem",
                    }}
                  >
                    Preferred Technical Skills
                  </h4>
                  <div
                    style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}
                  >
                    {viewingOpening.preferred_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        style={{
                          backgroundColor: "rgba(52, 211, 153, 0.15)",
                          color: "#6ee7b7",
                          border: "1px solid rgba(52, 211, 153, 0.3)",
                          padding: "0.2rem 0.6rem",
                          borderRadius: "4px",
                          fontSize: "0.82rem",
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            {/* Coursework & Examination */}
            <div
              style={{
                backgroundColor: "#0f172a",
                padding: "0.85rem",
                borderRadius: "6px",
                marginBottom: "1.25rem",
                fontSize: "0.875rem",
              }}
            >
              <div style={{ marginBottom: "0.5rem" }}>
                <strong style={{ color: "#f8fafc" }}>Prerequisites:</strong>{" "}
                <span style={{ color: "#94a3b8" }}>
                  {viewingOpening.prerequisites.join(", ")}
                </span>
              </div>
              <div>
                <strong style={{ color: "#f8fafc" }}>Exam Syllabus:</strong>{" "}
                <span style={{ color: "#94a3b8" }}>
                  {viewingOpening.syllabus_topics.join(", ")}
                </span>
              </div>
            </div>

            {/* Eligibility Threshold Summary */}
            <div className="opening-details" style={{ marginBottom: "1.5rem" }}>
              <div>
                <span>Min GPA:</span>{" "}
                <strong>{viewingOpening.min_gpa} / 10</strong>
              </div>
              <div>
                <span>Min GATE Score:</span>{" "}
                <strong>{viewingOpening.min_gate_score ?? "N/A"}</strong>
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ display: "flex", gap: "1rem" }}>
              <button
                onClick={() => setViewingOpening(null)}
                className="btn"
                style={{ background: "#334155", color: "#fff", flex: 1 }}
              >
                Close
              </button>

              {viewingOpening.status === "ACTIVE" &&
                !viewingOpening.has_applied && (
                  <button
                    onClick={() => {
                      setSelectedOpening(viewingOpening);
                      setViewingOpening(null);
                      setApplyError("");
                    }}
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                  >
                    Proceed to Apply &rarr;
                  </button>
                )}
            </div>
          </div>
        </div>
      )}

      {/* 2. Application Submission Modal */}
      {selectedOpening && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            zIndex: 100,
          }}
        >
          <div
            className="opening-card"
            style={{ maxWidth: "540px", maxHeight: "90vh", overflowY: "auto" }}
          >
            <h2
              className="opening-title"
              style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}
            >
              Apply for {selectedOpening.title} ({selectedOpening.program_type})
            </h2>

            {applyError && (
              <div
                className="alert alert-error"
                style={{ marginBottom: "1rem" }}
              >
                {applyError}
              </div>
            )}

            <form onSubmit={handleApplySubmit} className="opening-form">
              <div className="form-group-dark">
                <label className="form-label-dark">
                  Cumulative GPA (Out of 10.0)
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  className="form-input-dark"
                  placeholder={`Minimum required: ${selectedOpening.min_gpa}`}
                  value={gpaInput}
                  onChange={(e) => setGpaInput(e.target.value)}
                />
              </div>

              <div className="form-group-dark">
                <label className="form-label-dark">
                  GATE Score{" "}
                  {selectedOpening.min_gate_score ? "(Required)" : "(Optional)"}
                </label>
                <input
                  type="number"
                  step="1"
                  required={Boolean(selectedOpening.min_gate_score)}
                  className="form-input-dark"
                  placeholder={
                    selectedOpening.min_gate_score
                      ? `Min required: ${selectedOpening.min_gate_score}`
                      : "Optional"
                  }
                  value={gateInput}
                  onChange={(e) => setGateInput(e.target.value)}
                />
              </div>

              {/* Ph.D. Specific Resume PDF Upload Field */}
              {selectedOpening.program_type === "PhD" ? (
                <div className="form-group-dark">
                  <label className="form-label-dark">
                    Upload Resume / CV (PDF required for Ph.D. - Max 5MB)
                  </label>
                  <input
                    type="file"
                    accept=".pdf"
                    required
                    className="form-input-dark"
                    onChange={(e) => {
                      const selectedFile = e.target.files
                        ? e.target.files[0]
                        : null;

                      if (selectedFile) {
                        if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
                          setApplyError("Selected file must be in PDF format.");
                          e.target.value = "";
                          setResumeFile(null);
                          return;
                        }

                        if (selectedFile.size > 5 * 1024 * 1024) {
                          setApplyError(
                            "File size exceeds 5MB limit. Please choose a smaller resume.",
                          );
                          e.target.value = "";
                          setResumeFile(null);
                          return;
                        }
                      }

                      setApplyError("");
                      setResumeFile(selectedFile);
                    }}
                  />
                </div>
              ) : (
                <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                  * Resume upload is not required for M.Tech applications.
                </p>
              )}

              <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedOpening(null);
                    setResumeFile(null);
                    setGpaInput("");
                    setGateInput("");
                    setApplyError("");
                  }}
                  className="btn"
                  style={{ background: "#334155", color: "#fff", flex: 1 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {submitting ? "Submitting..." : "Submit Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
