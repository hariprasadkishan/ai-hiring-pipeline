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

interface InterviewSlotItem {
  slot_id: string;
  opening_id: string;
  start_time: string;
  end_time: string;
  is_booked: boolean;
  confirmation_code?: string | null;
}

interface BookingDetails {
  confirmation_code: string;
  slot_id: string;
  application_id: string;
  start_time: string;
  end_time: string;
  mock_calendar_event?: {
    event_id: string;
    summary: string;
    description: string;
    start: string;
    end: string;
    status: string;
    meeting_link: string;
  };
}

export default function StudentApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  // Scheduling State
  const [schedulingApp, setSchedulingApp] = useState<ApplicationItem | null>(null);
  const [slots, setSlots] = useState<InterviewSlotItem[]>([]);
  const [slotsLoading, setSlotsLoading] = useState<boolean>(false);
  const [bookingLoading, setBookingLoading] = useState<boolean>(false);
  const [bookingError, setBookingError] = useState<string>("");
  const [confirmationModal, setConfirmationModal] = useState<BookingDetails | null>(null);

  const fetchMyApplications = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/");
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
          router.push("/");
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
        return "Congratulations! You have been shortlisted. Please select an interview slot below to schedule your technical interview.";
      case "REJECTED":
        return "Your application was not selected for this position.";
      case "INTERVIEW_PENDING":
        return "Interview slot confirmed! Proceed to Identity Verification to begin your interactive AI interview.";
      case "ACCEPTED":
        return "Congratulations! Offer extended for admission.";
      case "COMPLETED":
        return "Admission evaluation process finalized.";
      case "APPLIED":
      default:
        return "Application submitted and under academic review.";
    }
  };

  const handleOpenScheduling = async (app: ApplicationItem) => {
    setSchedulingApp(app);
    setSlotsLoading(true);
    setBookingError("");
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/slots/${app.opening_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load interview slots.");
      const data = await res.json();
      setSlots(data);
    } catch (err: unknown) {
      if (err instanceof Error) setBookingError(err.message);
    } finally {
      setSlotsLoading(false);
    }
  };

  const handleBookSlot = async (slotId: string) => {
    if (!schedulingApp) return;
    setBookingLoading(true);
    setBookingError("");
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/slots/book`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          slot_id: slotId,
          application_id: schedulingApp.application_id,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Booking failed.");
      setConfirmationModal(data);
      setSchedulingApp(null);
      await fetchMyApplications();
    } catch (err: unknown) {
      if (err instanceof Error) setBookingError(err.message);
    } finally {
      setBookingLoading(false);
    }
  };

  const handleViewBooking = async (appId: string) => {
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/booking/${appId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load booking details.");
      const data = await res.json();
      setConfirmationModal(data);
    } catch (err: unknown) {
      if (err instanceof Error) alert(err.message);
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

                  {/* Scheduling / Interview Launch / View Report Buttons */}
                  {app.status === "SHORTLISTED" ? (
                    <button
                      onClick={() => handleOpenScheduling(app)}
                      style={{
                        backgroundColor: "#2563eb",
                        color: "#ffffff",
                        border: "none",
                        padding: "0.5rem 1.25rem",
                        borderRadius: "6px",
                        fontWeight: 700,
                        cursor: "pointer",
                        fontSize: "0.875rem",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        boxShadow: "0 2px 8px rgba(37, 99, 235, 0.3)",
                      }}
                    >
                      <span>📅</span> Schedule Interview Slot
                    </button>
                  ) : app.status === "INTERVIEW_PENDING" ? (
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <button
                        onClick={() => handleViewBooking(app.application_id)}
                        style={{
                          backgroundColor: "#334155",
                          color: "#cbd5e1",
                          border: "1px solid #475569",
                          padding: "0.5rem 0.85rem",
                          borderRadius: "6px",
                          fontWeight: 600,
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        🎟️ Booking Details
                      </button>
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
                        <span>🤖</span> Enter Interview Room
                      </button>
                    </div>
                  ) : app.status === "COMPLETED" ? (
                    <button
                      onClick={() =>
                        router.push(`/student/interview/${app.application_id}`)
                      }
                      style={{
                        backgroundColor: "#334155",
                        color: "#38bdf8",
                        border: "1px solid #0284c7",
                        padding: "0.5rem 1.25rem",
                        borderRadius: "6px",
                        fontWeight: 700,
                        cursor: "pointer",
                        fontSize: "0.875rem",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                      }}
                    >
                      <span>📋</span> View Interview Report
                    </button>
                  ) : null}
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

      {/* Scheduling Slot Picker Modal */}
      {schedulingApp && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            zIndex: 100,
          }}
        >
          <div
            className="opening-card"
            style={{
              maxWidth: "600px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
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
                <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#f8fafc" }}>
                  Schedule Your Interview
                </h2>
                <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#94a3b8" }}>
                  {schedulingApp.title} ({schedulingApp.department})
                </p>
              </div>
              <button
                onClick={() => setSchedulingApp(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                }}
              >
                &times;
              </button>
            </div>

            {bookingError && (
              <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
                {bookingError}
              </div>
            )}

            {slotsLoading ? (
              <div style={{ textAlign: "center", padding: "2rem", color: "#94a3b8" }}>
                <div className="spinner-large" />
                <p style={{ marginTop: "0.75rem" }}>Loading available calendar slots...</p>
              </div>
            ) : slots.length === 0 ? (
              <div style={{ textAlign: "center", padding: "2rem", color: "#94a3b8" }}>
                No slots currently available for this opening. Please contact the administrator.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#cbd5e1" }}>
                  Select an available interview slot (times in UTC):
                </p>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                    gap: "0.75rem",
                  }}
                >
                  {slots.map((slot) => {
                    const startDate = new Date(slot.start_time);
                    const endDate = new Date(slot.end_time);
                    return (
                      <div
                        key={slot.slot_id}
                        style={{
                          backgroundColor: slot.is_booked ? "#1e293b" : "#1e293b",
                          border: `1px solid ${slot.is_booked ? "#475569" : "#3b82f6"}`,
                          borderRadius: "6px",
                          padding: "0.85rem",
                          opacity: slot.is_booked ? 0.5 : 1,
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                          gap: "0.75rem",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, color: "#f8fafc", fontSize: "0.95rem" }}>
                            {startDate.toLocaleDateString("en-US", {
                              weekday: "short",
                              month: "short",
                              day: "numeric",
                            })}
                          </div>
                          <div style={{ color: "#38bdf8", fontSize: "0.85rem", marginTop: "0.2rem" }}>
                            {startDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -{" "}
                            {endDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </div>
                        </div>

                        {slot.is_booked ? (
                          <span
                            style={{
                              fontSize: "0.75rem",
                              color: "#94a3b8",
                              fontWeight: 600,
                              textAlign: "center",
                              backgroundColor: "#0f172a",
                              padding: "0.3rem",
                              borderRadius: "4px",
                            }}
                          >
                            Slot Booked
                          </span>
                        ) : (
                          <button
                            onClick={() => handleBookSlot(slot.slot_id)}
                            disabled={bookingLoading}
                            style={{
                              backgroundColor: "#2563eb",
                              color: "#ffffff",
                              border: "none",
                              borderRadius: "4px",
                              padding: "0.4rem 0.8rem",
                              fontSize: "0.85rem",
                              fontWeight: 600,
                              cursor: bookingLoading ? "not-allowed" : "pointer",
                            }}
                          >
                            {bookingLoading ? "Booking..." : "Confirm Slot"}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Booking Confirmation / Mock Calendar Modal */}
      {confirmationModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            zIndex: 100,
          }}
        >
          <div
            className="opening-card"
            style={{
              maxWidth: "580px",
              width: "100%",
              backgroundColor: "#0f172a",
              border: "2px solid #10b981",
              borderRadius: "8px",
            }}
          >
            <div style={{ textAlign: "center", marginBottom: "1rem" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  backgroundColor: "#065f46",
                  color: "#34d399",
                  borderRadius: "50%",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1.5rem",
                  marginBottom: "0.5rem",
                }}
              >
                ✓
              </div>
              <h2 style={{ margin: 0, color: "#f8fafc", fontSize: "1.3rem" }}>
                Interview Scheduled!
              </h2>
              <p style={{ margin: "0.25rem 0 0 0", color: "#94a3b8", fontSize: "0.85rem" }}>
                Confirmation Code: <strong style={{ color: "#38bdf8" }}>{confirmationModal.confirmation_code}</strong>
              </p>
            </div>

            <div
              style={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "6px",
                padding: "1rem",
                marginBottom: "1rem",
                fontSize: "0.85rem",
              }}
            >
              <div style={{ color: "#60a5fa", fontWeight: 700, marginBottom: "0.5rem" }}>
                📅 Scheduled Appointment
              </div>
              <div style={{ color: "#f8fafc", marginBottom: "0.25rem" }}>
                <strong>Date & Time:</strong> {new Date(confirmationModal.start_time).toUTCString()}
              </div>
              <div style={{ color: "#94a3b8", marginBottom: "0.5rem" }}>
                <strong>Platform:</strong> AI Technical Proctoring & Reasoning Chamber
              </div>

              {confirmationModal.mock_calendar_event && (
                <div style={{ marginTop: "0.75rem", borderTop: "1px solid #334155", paddingTop: "0.75rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "#34d399", fontWeight: 700, display: "block", marginBottom: "0.25rem" }}>
                    ✓ Mock Calendar JSON Generated (iCal Compatible)
                  </span>
                  <pre
                    style={{
                      backgroundColor: "#020617",
                      padding: "0.5rem",
                      borderRadius: "4px",
                      fontSize: "0.75rem",
                      color: "#94a3b8",
                      overflowX: "auto",
                      maxHeight: "120px",
                    }}
                  >
                    {JSON.stringify(confirmationModal.mock_calendar_event, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={() => setConfirmationModal(null)}
                style={{
                  flex: 1,
                  backgroundColor: "#334155",
                  color: "#f8fafc",
                  border: "none",
                  padding: "0.6rem",
                  borderRadius: "6px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Close
              </button>
              <button
                onClick={() => {
                  const appId = confirmationModal.application_id;
                  setConfirmationModal(null);
                  router.push(`/student/interview/${appId}`);
                }}
                style={{
                  flex: 1,
                  backgroundColor: "#10b981",
                  color: "#022c22",
                  border: "none",
                  padding: "0.6rem",
                  borderRadius: "6px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Enter Interview Room &rarr;
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
