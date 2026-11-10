"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CreateOpeningPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [programType, setProgramType] = useState<"MTech" | "PhD">("MTech");
  const [department, setDepartment] = useState(
    "Computer Science & Engineering",
  );

  // Job Description / Research Fields
  const [description, setDescription] = useState("");
  const [researchAreas, setResearchAreas] = useState("");
  const [preferredSkills, setPreferredSkills] = useState("");

  // Academic Thresholds & Coursework
  const [minGpa, setMinGpa] = useState("7.5");
  const [minGate, setMinGate] = useState("650");
  const [prerequisites, setPrerequisites] = useState(
    "Data Structures, Algorithms, OS",
  );
  const [syllabusTopics, setSyllabusTopics] = useState(
    "Distributed Systems, Computer Networks, Machine Learning",
  );

  // Application Window
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (new Date(endDate) <= new Date(startDate)) {
      setError("Application End Date must be after the Start Date.");
      return;
    }

    setLoading(true);

    const payload = {
      title,
      program_type: programType,
      department,
      description: description.trim() !== "" ? description.trim() : null,
      research_areas: researchAreas
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      preferred_skills: preferredSkills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      min_gpa: parseFloat(minGpa),
      min_gate_score: minGate.trim() !== "" ? parseFloat(minGate) : null,
      prerequisites: prerequisites
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      syllabus_topics: syllabusTopics
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      start_date: startDate,
      end_date: endDate,
    };

    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        throw new Error("Session expired. Please log in again.");
      }

      const response = await fetch(`${API_BASE_URL}/api/openings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "Failed to create opening");

      router.push("/teacher/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-opening-container">
      <div className="opening-card">
        <h1 className="opening-title">Post New Admission Opening</h1>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="opening-form">
          <div className="form-group-dark">
            <label className="form-label-dark">Opening Title</label>
            <input
              type="text"
              required
              className="form-input-dark"
              placeholder="e.g., Ph.D. Admissions in Vision AI / M.Tech AI 2026"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="form-grid-2">
            <div className="form-group-dark">
              <label className="form-label-dark">Program Degree</label>
              <select
                className="form-select-dark"
                value={programType}
                onChange={(e) =>
                  setProgramType(e.target.value as "MTech" | "PhD")
                }
              >
                <option value="MTech">M.Tech</option>
                <option value="PhD">Ph.D.</option>
              </select>
            </div>

            <div className="form-group-dark">
              <label className="form-label-dark">Department</label>
              <input
                type="text"
                required
                className="form-input-dark"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />
            </div>
          </div>

          {/* Expanded Job Description / Research Requirements Section */}
          <div
            style={{
              padding: "1rem",
              borderRadius: "8px",
              backgroundColor: "rgba(15, 23, 42, 0.5)",
              border: "1px solid #334155",
            }}
          >
            <h3
              style={{
                fontSize: "0.95rem",
                color: "#60a5fa",
                marginBottom: "0.75rem",
              }}
            >
              Job & Research Description{" "}
              {programType === "MTech"
                ? "(Optional)"
                : "(Recommended for Ph.D.)"}
            </h3>

            <div className="form-group-dark" style={{ marginBottom: "1rem" }}>
              <label className="form-label-dark">
                Project / Lab Description
              </label>
              <textarea
                className="form-input-dark"
                rows={3}
                placeholder="Briefly describe the research lab, funded project scope, or candidate expectations..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                style={{ resize: "vertical" }}
              />
            </div>

            <div className="form-grid-2">
              <div className="form-group-dark">
                <label className="form-label-dark">
                  Research Areas (Comma Separated)
                </label>
                <input
                  type="text"
                  className="form-input-dark"
                  placeholder="e.g., Computer Vision, LLMs, Federated Learning"
                  value={researchAreas}
                  onChange={(e) => setResearchAreas(e.target.value)}
                />
              </div>

              <div className="form-group-dark">
                <label className="form-label-dark">
                  Preferred Skills / Tech Stack (Comma Separated)
                </label>
                <input
                  type="text"
                  className="form-input-dark"
                  placeholder="e.g., PyTorch, CUDA, ROS2, Docker"
                  value={preferredSkills}
                  onChange={(e) => setPreferredSkills(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Application Window Constraints */}
          <div className="date-window-box">
            <div className="form-group-dark">
              <label className="form-label-dark label-start-date">
                Application Open Date
              </label>
              <input
                type="datetime-local"
                required
                className="form-input-dark"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="form-group-dark">
              <label className="form-label-dark label-end-date">
                Application Deadline
              </label>
              <input
                type="datetime-local"
                required
                className="form-input-dark"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <div className="form-grid-2">
            <div className="form-group-dark">
              <label className="form-label-dark">Minimum GPA (out of 10)</label>
              <input
                type="number"
                step="0.1"
                required
                className="form-input-dark"
                value={minGpa}
                onChange={(e) => setMinGpa(e.target.value)}
              />
            </div>

            <div className="form-group-dark">
              <label className="form-label-dark">
                Minimum GATE Score (Optional)
              </label>
              <input
                type="number"
                className="form-input-dark"
                placeholder="N/A for PhD"
                value={minGate}
                onChange={(e) => setMinGate(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group-dark">
            <label className="form-label-dark">
              Prerequisite Subjects (Comma Separated)
            </label>
            <input
              type="text"
              required
              className="form-input-dark"
              value={prerequisites}
              onChange={(e) => setPrerequisites(e.target.value)}
            />
          </div>

          <div className="form-group-dark">
            <label className="form-label-dark">
              Interview Syllabus Topics (Comma Separated)
            </label>
            <input
              type="text"
              required
              className="form-input-dark"
              value={syllabusTopics}
              onChange={(e) => setSyllabusTopics(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary publish-btn"
          >
            {loading ? (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <svg className="spinner" viewBox="0 0 24 24">
                  <circle
                    style={{ opacity: 0.25 }}
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    style={{ opacity: 0.75 }}
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Publishing Opening...
              </span>
            ) : (
              "Publish Admission Opening"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
