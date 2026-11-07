"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MessageItem {
  sender: "AI" | "CANDIDATE";
  content: string;
  turn_score?: number;
}

interface EvaluationReport {
  overall_score?: number;
  technical_depth_score?: number;
  problem_solving_score?: number;
  domain_knowledge_score?: number;
  communication_score?: number;
  strengths?: string[];
  weaknesses?: string[];
  summary_reasoning?: string;
  recommendation?: "RECOMMENDED" | "BORDERLINE" | "REJECTED";
}

export default function StudentInterviewPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params?.applicationId as string;

  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(5);
  const [inputValue, setInputValue] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [finalReport, setFinalReport] = useState<EvaluationReport | null>(null);

  // Behavioral Telemetry
  const [tabSwitches, setTabSwitches] = useState<number>(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, submitting]);

  // Tab switch anomaly counter
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setTabSwitches((prev) => prev + 1);
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  // Initialize or resume session directly inside useEffect
  useEffect(() => {
    if (!applicationId) return;

    let isMounted = true;

    const fetchSession = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/api/interview/start`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ application_id: applicationId }),
        });

        if (!res.ok) {
          throw new Error("Failed to start or resume interview session.");
        }

        const data = await res.json();
        if (!isMounted) return;

        setSessionId(data.session_id);
        setCurrentQuestionIndex(data.current_question_index);
        setTotalQuestions(data.total_questions);

        if (data.is_completed) {
          setIsCompleted(true);
          setFinalReport(data.final_report);
        } else if (data.current_question) {
          setMessages([{ sender: "AI", content: data.current_question }]);
        }
      } catch (err: unknown) {
        if (isMounted && err instanceof Error) {
          setError(err.message);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchSession();

    return () => {
      isMounted = false;
    };
  }, [applicationId, router]);

  // Submit candidate response
  const handleSendResponse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || submitting || isCompleted) return;

    const candidateText = inputValue.trim();
    setInputValue("");
    setSubmitting(true);
    setError("");

    setMessages((prev) => [
      ...prev,
      { sender: "CANDIDATE", content: candidateText },
    ]);

    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/respond`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          candidate_response: candidateText,
          telemetry_data: { tab_switches: tabSwitches },
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to process your response. Please try again.");
      }

      const data = await res.json();

      if (data.last_turn_score !== undefined && data.last_turn_score !== null) {
        setMessages((prev) => {
          const updated = [...prev];
          const lastCandIdx = updated.findLastIndex(
            (m) => m.sender === "CANDIDATE",
          );
          if (lastCandIdx !== -1) {
            updated[lastCandIdx].turn_score = data.last_turn_score;
          }
          return updated;
        });
      }

      setCurrentQuestionIndex(data.current_question_index);

      if (data.is_completed) {
        setIsCompleted(true);
        setFinalReport(data.final_report);
      } else if (data.current_question) {
        setMessages((prev) => [
          ...prev,
          { sender: "AI", content: data.current_question },
        ]);
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "5rem", color: "#94a3b8" }}>
        <div className="spinner-large" />
        <p style={{ marginTop: "1rem" }}>
          Connecting to AI Interview Agent state engine...
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "1.5rem auto",
        padding: "0 1rem",
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 5rem)",
      }}
    >
      {/* Top Session Progress Bar */}
      <header
        style={{
          backgroundColor: "#1e293b",
          border: "1px solid #334155",
          borderRadius: "8px 8px 0 0",
          padding: "1rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem", color: "#f8fafc" }}>
            Academic Evaluation Session
          </h2>
          <p style={{ margin: 0, fontSize: "0.8rem", color: "#94a3b8" }}>
            Turn {Math.min(currentQuestionIndex + 1, totalQuestions)} of{" "}
            {totalQuestions}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {tabSwitches > 0 && (
            <span
              style={{
                backgroundColor: "#881337",
                color: "#f43f5e",
                padding: "0.25rem 0.6rem",
                borderRadius: "4px",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              ⚠️ Tab Switches: {tabSwitches}
            </span>
          )}
          <button
            onClick={() => router.push("/student/applications")}
            style={{
              backgroundColor: "#334155",
              color: "#cbd5e1",
              border: "none",
              padding: "0.4rem 0.8rem",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            Exit Session
          </button>
        </div>
      </header>

      {/* Main Chat Scroll Container */}
      <div
        style={{
          flex: 1,
          backgroundColor: "#0f172a",
          borderLeft: "1px solid #334155",
          borderRight: "1px solid #334155",
          padding: "1.5rem",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems:
                msg.sender === "CANDIDATE" ? "flex-end" : "flex-start",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                color: "#64748b",
                marginBottom: "0.25rem",
                marginLeft: msg.sender === "AI" ? "0.25rem" : 0,
                marginRight: msg.sender === "CANDIDATE" ? "0.25rem" : 0,
              }}
            >
              {msg.sender === "AI" ? "AI Interviewer" : "You"}
            </span>

            <div
              style={{
                maxWidth: "80%",
                padding: "0.85rem 1.15rem",
                borderRadius:
                  msg.sender === "CANDIDATE"
                    ? "16px 16px 2px 16px"
                    : "16px 16px 16px 2px",
                backgroundColor:
                  msg.sender === "CANDIDATE" ? "#2563eb" : "#1e293b",
                color: "#f8fafc",
                border: msg.sender === "AI" ? "1px solid #334155" : "none",
                fontSize: "0.95rem",
                lineHeight: "1.5",
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.content}
            </div>

            {msg.sender === "CANDIDATE" && msg.turn_score !== undefined && (
              <span
                style={{
                  fontSize: "0.7rem",
                  color: msg.turn_score >= 70 ? "#34d399" : "#fbbf24",
                  marginTop: "0.25rem",
                  marginRight: "0.25rem",
                }}
              >
                Evaluated Score: {msg.turn_score}/100
              </span>
            )}
          </div>
        ))}

        {submitting && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              color: "#94a3b8",
            }}
          >
            <div className="spinner-small" />
            <span style={{ fontSize: "0.85rem" }}>
              Evaluating response and planning next question...
            </span>
          </div>
        )}

        {/* Final Evaluation Report */}
        {isCompleted && finalReport && (
          <div
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #10b981",
              borderRadius: "8px",
              padding: "1.5rem",
              marginTop: "1rem",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
              }}
            >
              <h3 style={{ margin: 0, color: "#34d399" }}>
                🎉 Interview Completed
              </h3>
              <span
                style={{
                  backgroundColor:
                    finalReport.recommendation === "RECOMMENDED"
                      ? "#065f46"
                      : "#78350f",
                  color:
                    finalReport.recommendation === "RECOMMENDED"
                      ? "#34d399"
                      : "#fbbf24",
                  padding: "0.3rem 0.8rem",
                  borderRadius: "9999px",
                  fontSize: "0.8rem",
                  fontWeight: 700,
                }}
              >
                {finalReport.recommendation}
              </span>
            </div>

            <p
              style={{
                color: "#e2e8f0",
                fontSize: "0.9rem",
                lineHeight: "1.5",
                marginBottom: "1rem",
              }}
            >
              {finalReport.summary_reasoning}
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
                fontSize: "0.85rem",
              }}
            >
              <div>
                <h4 style={{ color: "#34d399", margin: "0 0 0.5rem 0" }}>
                  Strengths
                </h4>
                <ul
                  style={{ margin: 0, paddingLeft: "1.2rem", color: "#cbd5e1" }}
                >
                  {finalReport.strengths?.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 style={{ color: "#fbbf24", margin: "0 0 0.5rem 0" }}>
                  Areas for Improvement
                </h4>
                <ul
                  style={{ margin: 0, paddingLeft: "1.2rem", color: "#cbd5e1" }}
                >
                  {finalReport.weaknesses?.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {error && (
        <div
          style={{
            backgroundColor: "#881337",
            color: "#f43f5e",
            padding: "0.5rem 1rem",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Input Form */}
      <form
        onSubmit={handleSendResponse}
        style={{
          backgroundColor: "#1e293b",
          border: "1px solid #334155",
          borderRadius: "0 0 8px 8px",
          padding: "1rem",
          display: "flex",
          gap: "0.75rem",
        }}
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={
            isCompleted
              ? "Interview completed. Thank you!"
              : "Type your academic response..."
          }
          disabled={submitting || isCompleted}
          style={{
            flex: 1,
            backgroundColor: "#0f172a",
            border: "1px solid #334155",
            borderRadius: "6px",
            padding: "0.75rem 1rem",
            color: "#f8fafc",
            fontSize: "0.95rem",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={submitting || isCompleted || !inputValue.trim()}
          style={{
            backgroundColor: submitting || isCompleted ? "#334155" : "#2563eb",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            padding: "0 1.5rem",
            fontWeight: 600,
            cursor: submitting || isCompleted ? "not-allowed" : "pointer",
          }}
        >
          {submitting ? "Sending..." : "Submit Answer"}
        </button>
      </form>
    </div>
  );
}
