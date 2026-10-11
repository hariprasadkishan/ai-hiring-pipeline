"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Opening {
  opening_id: string;
  title: string;
  program_type: "MTech" | "PhD";
  department: string;
  min_gpa: number;
  min_gate_score: number | null;
  start_date: string;
  end_date: string;
  status: "UPCOMING" | "ACTIVE" | "CLOSED";
}

export default function TeacherDashboard() {
  const router = useRouter();
  const [openings, setOpenings] = useState<Opening[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchTeacherOpenings = async () => {
      const token = localStorage.getItem("access_token");

      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/openings/teacher`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            localStorage.removeItem("access_token");
            router.push("/login");
            return;
          }
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to load openings.");
        }

        const data: Opening[] = await response.json();
        setOpenings(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("An unexpected error occurred while fetching openings.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchTeacherOpenings();
  }, [router]);

  // Compute metric stats
  const totalOpenings = openings.length;
  const activeOpenings = openings.filter((op) => op.status === "ACTIVE").length;
  const upcomingOpenings = openings.filter(
    (op) => op.status === "UPCOMING",
  ).length;
  const closedOpenings = openings.filter((op) => op.status === "CLOSED").length;

  return (
    <div className="dashboard-container">
      {/* Top Header */}
      <header className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Faculty Portal</h1>
          <p className="dashboard-subtitle">
            View and manage your active and past postgraduate admission openings
          </p>
        </div>
        <Link href="/teacher/create-opening" className="btn btn-primary">
          + Create New Opening
        </Link>
      </header>

      {/* Summary Metrics Bar */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Total Posted</span>
          <span className="stat-value">{totalOpenings}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Active Windows</span>
          <span className="stat-value text-success">{activeOpenings}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Upcoming</span>
          <span className="stat-value text-warning">{upcomingOpenings}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Closed</span>
          <span className="stat-value text-muted-val">{closedOpenings}</span>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="alert alert-error" style={{ marginBottom: "1.5rem" }}>
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner-large" />
          <p>Fetching your admission openings...</p>
        </div>
      ) : openings.length === 0 ? (
        /* Empty State */
        <div className="empty-state">
          <h3>No Openings Created Yet</h3>
          <p>
            You have not posted any admission requirements for M.Tech or Ph.D.
            candidates.
          </p>
          <Link
            href="/teacher/create-opening"
            className="btn btn-primary"
            style={{ marginTop: "1rem" }}
          >
            Post Your First Opening
          </Link>
        </div>
      ) : (
        /* Openings Grid */
        <div className="openings-grid">
          {openings.map((opening) => (
            <div key={opening.opening_id} className="opening-card-dash">
              {/* Card Header Badges */}
              <div className="opening-card-header">
                <span
                  className={`badge badge-degree ${opening.program_type.toLowerCase()}`}
                >
                  {opening.program_type === "MTech" ? "M.Tech" : "Ph.D."}
                </span>
                <span
                  className={`badge badge-status status-${opening.status.toLowerCase()}`}
                >
                  {opening.status}
                </span>
              </div>

              {/* Title & Department */}
              <h3 className="opening-card-title">{opening.title}</h3>
              <p className="opening-card-dept">{opening.department}</p>

              {/* Requirement Summary Box */}
              <div className="opening-details">
                <div className="detail-item">
                  <span>Min GPA:</span> <strong>{opening.min_gpa} / 10</strong>
                </div>
                <div className="detail-item">
                  <span>Min GATE:</span>{" "}
                  <strong>
                    {opening.min_gate_score !== null
                      ? opening.min_gate_score
                      : "N/A"}
                  </strong>
                </div>
              </div>

              {/* Dates & Actions */}
              <div className="opening-card-footer">
                <div className="date-group">
                  <span>
                    Open: {new Date(opening.start_date).toLocaleDateString()}
                  </span>
                  <span>
                    Close: {new Date(opening.end_date).toLocaleDateString()}
                  </span>
                </div>

                <Link
                  href={`/teacher/openings/${opening.opening_id}/applications`}
                  className="btn-link"
                >
                  View Applicants &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
