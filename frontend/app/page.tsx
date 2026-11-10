"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import "@/styles/auth.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();

  const [isRegistering, setIsRegistering] = useState<boolean>(false);
  const [role, setRole] = useState<"student" | "teacher">("student");

  const [name, setName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [department, setDepartment] = useState<string>("");
  const [phone, setPhone] = useState<string>("");

  const [error, setError] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    const recruiterDomain = process.env.NEXT_PUBLIC_RECRUITER_DOMAIN || "";
    if (
      isRegistering &&
      role === "teacher" &&
      recruiterDomain &&
      !email.endsWith(recruiterDomain)
    ) {
      setError(
        `Staff registration is restricted to official ${recruiterDomain} accounts only.`,
      );
      setLoading(false);
      return;
    }

    const endpoint = isRegistering ? "/api/auth/register" : "/api/auth/login";
    const payload = isRegistering
      ? { name, email, password, role, department, phone }
      : { email, password, selected_role: role };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Authentication failed. Please check your credentials.",
        );
      }

      if (isRegistering) {
        setMessage("Account registered successfully! Please sign in.");
        setIsRegistering(false);
        setPassword("");
      } else {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("user_name", data.name);
        localStorage.setItem("user_id", data.user_id);

        if (data.role === "teacher") {
          router.push("/teacher/dashboard");
        } else {
          router.push("/student/openings");
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-wrapper">
      <div className="auth-card">
        {/* Header Icon & Title */}
        <header className="auth-header">
          <div className="auth-badge">
            <svg
              style={{ width: "2rem", height: "2rem" }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 14l9-5-9-5-9 5 9 5z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0112 20.055a11.952 11.952 0 01-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"
              />
            </svg>
          </div>
          <h1 className="auth-title">Academic Assessment System</h1>
          <p className="auth-subtitle">
            {isRegistering
              ? "Create your institutional account"
              : "Sign in to access your portal"}
          </p>
        </header>

        {/* Role Toggle Tabs */}
        <div className="role-tabs">
          <button
            type="button"
            className={`tab-btn ${role === "student" ? "active" : ""}`}
            onClick={() => {
              setRole("student");
              setError("");
            }}
          >
            Student Portal
          </button>
          <button
            type="button"
            className={`tab-btn ${role === "teacher" ? "active" : ""}`}
            onClick={() => {
              setRole("teacher");
              setError("");
            }}
          >
            Faculty Portal
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="alert-box alert-error">
            <svg
              style={{ width: "1rem", height: "1rem", flexShrink: 0 }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Success Alert */}
        {message && (
          <div className="alert-box alert-success">
            <svg
              style={{ width: "1rem", height: "1rem", flexShrink: 0 }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{message}</span>
          </div>
        )}

        {/* Form Controls */}
        <form onSubmit={handleSubmit} className="auth-form">
          {isRegistering && (
            <div className="field-group">
              <label className="field-label">Full Name</label>
              <input
                type="text"
                required
                className="field-input"
                placeholder={
                  role === "teacher" ? "Prof. Alan Turing" : "John Doe"
                }
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          )}

          <div className="field-group">
            <label className="field-label">Institutional Email</label>
            <input
              type="email"
              required
              className="field-input"
              placeholder={
                role === "teacher"
                  ? "faculty@iiitdwd.ac.in"
                  : "student@iiitdwd.ac.in"
              }
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="field-group">
            <label className="field-label">Password</label>
            <input
              type="password"
              required
              className="field-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {isRegistering && role === "teacher" && (
            <div className="field-group">
              <label className="field-label">Academic Department</label>
              <input
                type="text"
                required
                className="field-input"
                placeholder="Computer Science & Engineering"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />
            </div>
          )}

          {isRegistering && role === "student" && (
            <div className="field-group">
              <label className="field-label">
                Contact Phone Number (Optional)
              </label>
              <input
                type="text"
                className="field-input"
                placeholder="+1 (555) 019-2834"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
          )}

          <button type="submit" disabled={loading} className="submit-btn">
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
                Processing...
              </span>
            ) : isRegistering ? (
              `Register as ${role === "teacher" ? "Faculty Member" : "Student"}`
            ) : (
              `Sign in to ${role === "teacher" ? "Faculty Portal" : "Student Portal"}`
            )}
          </button>
        </form>

        {/* Footer Toggle Button */}
        <footer className="auth-footer">
          <button
            type="button"
            className="toggle-mode-btn"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
              setMessage("");
            }}
          >
            {isRegistering
              ? "Already registered? Sign in to your account"
              : "Don't have an institutional account? Register here"}
          </button>
        </footer>
      </div>
    </main>
  );
}
