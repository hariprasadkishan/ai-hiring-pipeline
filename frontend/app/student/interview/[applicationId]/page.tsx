"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import VideoProctor, { ProctoringTelemetry } from "@/components/VideoProctor";
import "@/styles/teacher-opening.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MessageItem {
  sender: "AI" | "CANDIDATE";
  content: string;
  turn_score?: number;
  turn_feedback?: {
    decision?: string;
    trigger_phrase_from_candidate?: string;
    reasoning?: string;
    competency?: string;
    feedback?: string;
  };
}

interface EvaluationReport {
  overall_score?: number;
  technical_depth_score?: number;
  problem_solving_score?: number;
  domain_knowledge_score?: number;
  communication_score?: number;
  competency_scores?: Record<string, number>;
  stage5_composite?: {
    resume_score: number;
    interview_score: number;
    composite_score: number;
    weight_resume: number;
    weight_interview: number;
  };
  strengths?: string[];
  weaknesses?: string[];
  summary_reasoning?: string;
  recommendation?: "RECOMMENDED" | "BORDERLINE" | "REJECTED";
}

export default function StudentInterviewPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params?.applicationId as string;

  // Session & Chat State
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(5);
  const [currentQuestion, setCurrentQuestion] = useState<string>("");
  const [currentDecision, setCurrentDecision] = useState<string>("opening_question");
  const [latestReasoning, setLatestReasoning] = useState<string>("");
  const [questionLoading, setQuestionLoading] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(true);
  const [inputValue, setInputValue] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [finalReport, setFinalReport] = useState<EvaluationReport | null>(null);

  // STAGE 3: Identity Verification (HARD GATE) State
  const [identityVerified, setIdentityVerified] = useState<boolean>(false);
  const [identityStatus, setIdentityStatus] = useState<string>("NOT_VERIFIED");
  const [identityConfidence, setIdentityConfidence] = useState<number>(0);
  const [identityReason, setIdentityReason] = useState<string>("");
  const [verifyingIdentity, setVerifyingIdentity] = useState<boolean>(false);
  const [referencePhoto, setReferencePhoto] = useState<string>("/sample_reference_face.jpg");
  const [customRefPhoto, setCustomRefPhoto] = useState<string | null>(null);

  // STAGE 4: Voice Speech-To-Text & Text-To-Speech State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [ttsEnabled, setTtsEnabled] = useState<boolean>(true);
  const [speaking, setSpeaking] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);
  const ttsEnabledRef = useRef<boolean>(ttsEnabled);

  useEffect(() => {
    ttsEnabledRef.current = ttsEnabled;
  }, [ttsEnabled]);

  // Active Question resolution (guarantees question visibility from state or message stream)
  const activeQuestion =
    currentQuestion ||
    (messages.length > 0
      ? [...messages].reverse().find((m) => m.sender === "AI")?.content
      : "") ||
    "";

  useEffect(() => {
    if (!currentQuestion && activeQuestion) {
      setCurrentQuestion(activeQuestion);
    }
  }, [activeQuestion, currentQuestion]);

  // Live Proctoring & Anti-Swap Telemetry
  const [proctoringTelemetry, setProctoringTelemetry] = useState<ProctoringTelemetry>({
    violations_count: 0,
    tab_switches: 0,
    events: [],
  });

  // Verification Webcam Refs
  const gateVideoRef = useRef<HTMLVideoElement>(null);
  const gateCanvasRef = useRef<HTMLCanvasElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, submitting]);

  const handleTelemetryUpdate = useCallback((telemetry: ProctoringTelemetry) => {
    setProctoringTelemetry(telemetry);
  }, []);

  // Text-To-Speech Synthesizer with Chrome resilience
  const speakText = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) return;
    try {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*_#`]/g, "");
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = (e) => {
        console.warn("TTS playback warning/interrupted:", e);
        setSpeaking(false);
      };
      setTimeout(() => {
        try {
          window.speechSynthesis.speak(utterance);
        } catch (e) {
          console.warn("SpeechSynthesis speak exception:", e);
          setSpeaking(false);
        }
      }, 50);
    } catch (e) {
      console.error("Speech synthesis error:", e);
      setSpeaking(false);
    }
  }, []);

  // Initialize Speech-To-Text (Web Speech API)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        let finalTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + " ";
          }
        }
        if (finalTranscript) {
          setInputValue((prev) => (prev ? prev + " " + finalTranscript.trim() : finalTranscript.trim()));
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleVoiceRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. You can type your answer in the text field.");
      return;
    }
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (e) {
        console.error("Failed starting speech recognition:", e);
      }
    }
  };

  // 1. Check Identity Status & Fetch Session on Mount
  const checkGateAndFetch = useCallback(async () => {
    if (!applicationId) return;
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/");
      return;
    }

    try {
      setLoading(true);
      setError("");

      // Step A: Check Stage 3 Hard Gate Status
      const gateRes = await fetch(`${API_BASE_URL}/api/interview/identity-status/${applicationId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (gateRes.ok) {
        const gateData = await gateRes.json();
        if (gateData.passed) {
          setIdentityVerified(true);
          setIdentityStatus("PASS");
          setIdentityConfidence(gateData.confidence || 1.0);
        } else {
          setIdentityVerified(false);
          setIdentityStatus(gateData.status);
          setIdentityReason(gateData.reason || "");
          setLoading(false);
          return;
        }
      }

      // Step B: Start or Resume Session (If Gate Passed)
      setQuestionLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/interview/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ application_id: applicationId }),
      });

      if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        if (errData.detail?.error === "IDENTITY_HARD_GATE_BLOCKED") {
          setIdentityVerified(false);
          setIdentityStatus(errData.detail.identity_status || "NOT_VERIFIED");
          setIdentityReason(errData.detail.message || "Stage 3 biometric verification required.");
          setLoading(false);
          setQuestionLoading(false);
          return;
        }
        throw new Error(errData.detail?.message || errData.detail || "Access denied.");
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to initialize interview.");
      }

      const data = await res.json();
      setIdentityVerified(true);
      setSessionId(data.session_id);
      setCurrentQuestionIndex(data.current_question_index);
      setTotalQuestions(data.total_questions || 5);
      if (data.agentic_action) setCurrentDecision(data.agentic_action);
      if (data.last_turn_feedback) setLatestReasoning(data.last_turn_feedback);

      // Populate full message history if returned from backend
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages.map((m: any) => ({
          sender: m.sender,
          content: m.content,
          turn_score: m.turn_score,
          turn_feedback: m.turn_feedback,
        })));
      }

      if (data.is_completed) {
        setIsCompleted(true);
        setFinalReport(data.final_report);
        setCurrentQuestion("");
      } else if (data.current_question) {
        setCurrentQuestion(data.current_question);
        if (!data.messages || data.messages.length === 0) {
          setMessages([{ sender: "AI", content: data.current_question }]);
        }
        if (ttsEnabledRef.current) {
          speakText(data.current_question);
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
      setQuestionLoading(false);
    }
  }, [applicationId, router, speakText]);

  useEffect(() => {
    checkGateAndFetch();
  }, [checkGateAndFetch]);

  // Stage 3: Mount Webcam Stream for Verification Gate
  useEffect(() => {
    if (identityVerified || loading) return;
    let stream: MediaStream | null = null;

    navigator.mediaDevices
      ?.getUserMedia({ video: { width: 480, height: 360, facingMode: "user" } })
      .then((s) => {
        stream = s;
        if (gateVideoRef.current) {
          gateVideoRef.current.srcObject = s;
          gateVideoRef.current.play();
        }
      })
      .catch((e) => {
        console.warn("Gate camera init error:", e);
      });

    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [identityVerified, loading]);

  // Stage 3: Handle Live Biometric Verification (HARD GATE)
  const handleVerifyIdentity = async () => {
    const video = gateVideoRef.current;
    const canvas = gateCanvasRef.current;
    if (!video || !canvas) {
      alert("Camera stream is not ready. Please allow webcam permissions.");
      return;
    }

    setVerifyingIdentity(true);
    setError("");

    try {
      canvas.width = video.videoWidth || 480;
      canvas.height = video.videoHeight || 360;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas context unavailable.");

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const liveFrameB64 = canvas.toDataURL("image/jpeg", 0.85);

      // Fetch sample or custom reference photo
      let refPhotoB64 = customRefPhoto;
      if (!refPhotoB64) {
        try {
          const refRes = await fetch(referencePhoto);
          const refBlob = await refRes.blob();
          refPhotoB64 = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result as string);
            reader.readAsDataURL(refBlob);
          });
        } catch (e) {
          console.warn("Could not load sample reference photo, using live fallback", e);
        }
      }

      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE_URL}/api/interview/verify-identity`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          application_id: applicationId,
          live_frame: liveFrameB64,
          reference_photo: refPhotoB64,
          check_type: "ENTRY_HARD_GATE",
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Identity verification call failed.");

      setIdentityStatus(data.status);
      setIdentityConfidence(data.confidence);
      setIdentityReason(data.reason);

      if (data.passed) {
        setIdentityVerified(true);
        setQuestionLoading(true);
        setError("");

        try {
          // Start interview now that hard gate passed
          const startRes = await fetch(`${API_BASE_URL}/api/interview/start`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ application_id: applicationId }),
          });
          const startData = await startRes.json();
          if (!startRes.ok) {
            throw new Error(startData.detail?.message || startData.detail || "Failed to initialize interview.");
          }

          setSessionId(startData.session_id);
          setCurrentQuestionIndex(startData.current_question_index);
          setTotalQuestions(startData.total_questions || 5);
          if (startData.agentic_action) setCurrentDecision(startData.agentic_action);

          if (startData.is_completed) {
            setIsCompleted(true);
            setFinalReport(startData.final_report);
            setCurrentQuestion("");
          } else if (startData.current_question) {
            setCurrentQuestion(startData.current_question);
            if (startData.messages && startData.messages.length > 0) {
              setMessages(startData.messages.map((m: any) => ({
                sender: m.sender,
                content: m.content,
                turn_score: m.turn_score,
                turn_feedback: m.turn_feedback,
              })));
            } else {
              setMessages([{ sender: "AI", content: startData.current_question }]);
            }
            if (ttsEnabledRef.current) speakText(startData.current_question);
          }
        } catch (startErr: unknown) {
          if (startErr instanceof Error) setError(`Session initialization: ${startErr.message}`);
        } finally {
          setQuestionLoading(false);
        }
      } else {
        setIdentityVerified(false);
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setVerifyingIdentity(false);
      setQuestionLoading(false);
    }
  };

  // Submit candidate response
  const handleSendResponse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || submitting || isCompleted) return;

    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }

    const candidateText = inputValue.trim();
    setInputValue("");
    setSubmitting(true);
    setQuestionLoading(true);
    setError("");

    setMessages((prev) => [
      ...prev,
      { sender: "CANDIDATE", content: candidateText },
    ]);

    // Anti-swap snapshot capture from hidden video canvas
    let liveFrameSnapshot: string | null = null;
    try {
      const activeVideo = document.querySelector("video") as HTMLVideoElement | null;
      if (activeVideo && activeVideo.readyState >= 2) {
        const offscreenCanvas = document.createElement("canvas");
        offscreenCanvas.width = 320;
        offscreenCanvas.height = 240;
        const ctx = offscreenCanvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(activeVideo, 0, 0, 320, 240);
          liveFrameSnapshot = offscreenCanvas.toDataURL("image/jpeg", 0.7);
        }
      }
    } catch (e) {
      console.warn("Anti-swap frame snapshot failed:", e);
    }

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
          telemetry_data: {
            violations_count: proctoringTelemetry.violations_count,
            tab_switches: proctoringTelemetry.tab_switches,
            events: proctoringTelemetry.events,
            live_frame: liveFrameSnapshot,
          },
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to process your response.");
      }

      const data = await res.json();

      setCurrentQuestionIndex(data.current_question_index);
      if (data.agentic_action) setCurrentDecision(data.agentic_action);
      if (data.last_turn_feedback) setLatestReasoning(data.last_turn_feedback);

      // Populate synchronized message transcript
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages.map((m: any) => ({
          sender: m.sender,
          content: m.content,
          turn_score: m.turn_score,
          turn_feedback: m.turn_feedback,
        })));
      } else if (data.last_turn_score !== undefined && data.last_turn_score !== null) {
        setMessages((prev) => {
          const updated = [...prev];
          const lastCandIdx = updated.findLastIndex((m) => m.sender === "CANDIDATE");
          if (lastCandIdx !== -1) {
            updated[lastCandIdx].turn_score = data.last_turn_score;
          }
          return updated;
        });
      }

      if (data.is_completed) {
        setIsCompleted(true);
        setFinalReport(data.final_report);
        setCurrentQuestion("");
        if (ttsEnabledRef.current) {
          speakText("Thank you. The interview session is now complete. Your final evaluation report is ready.");
        }
      } else if (data.current_question) {
        setCurrentQuestion(data.current_question);
        if (!data.messages || data.messages.length === 0) {
          setMessages((prev) => [
            ...prev,
            {
              sender: "AI",
              content: data.current_question,
              turn_feedback: {
                decision: data.agentic_action || "next_competency",
                reasoning: data.last_turn_feedback,
              },
            },
          ]);
        }
        if (ttsEnabledRef.current) {
          speakText(data.current_question);
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setSubmitting(false);
      setQuestionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "5rem", color: "#94a3b8" }}>
        <div className="spinner-large" />
        <p style={{ marginTop: "1rem" }}>
          Connecting to AI Interview Agent state engine & verifying proctoring stream...
        </p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // STAGE 3: IDENTITY VERIFICATION (HARD GATE) SCREEN
  // -------------------------------------------------------------------------
  if (!identityVerified) {
    return (
      <div
        style={{
          maxWidth: "760px",
          width: "100%",
          margin: "2rem auto",
          padding: "1rem",
        }}
      >
        <div
          style={{
            backgroundColor: "#1e293b",
            border: "2px solid #3b82f6",
            borderRadius: "12px",
            padding: "2rem",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.5rem" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                backgroundColor: "#1d4ed8",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.5rem",
              }}
            >
              🛡️
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.35rem", color: "#f8fafc", fontWeight: 700 }}>
                Stage 3: Identity Verification (HARD GATE)
              </h2>
              <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#94a3b8" }}>
                Mandatory biometric security gate. Real face detection and reference photo matching must pass before entry.
              </p>
            </div>
          </div>

          {/* Dual Visual Panels: Live Camera & Reference Photo */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1.5rem",
              marginBottom: "1.5rem",
            }}
          >
            {/* Live Camera View */}
            <div>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", display: "block", marginBottom: "0.5rem" }}>
                1. Live Webcam Feed
              </label>
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "220px",
                  backgroundColor: "#0f172a",
                  borderRadius: "8px",
                  overflow: "hidden",
                  border: "2px solid #334155",
                }}
              >
                <video
                  ref={gateVideoRef}
                  playsInline
                  muted
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
                <canvas ref={gateCanvasRef} style={{ display: "none" }} />
                {/* Visual Target Reticle */}
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    width: "120px",
                    height: "150px",
                    border: "2px dashed #38bdf8",
                    borderRadius: "50%",
                    pointerEvents: "none",
                  }}
                />
                <span
                  style={{
                    position: "absolute",
                    bottom: "8px",
                    left: "8px",
                    backgroundColor: "rgba(15, 23, 42, 0.8)",
                    color: "#38bdf8",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontSize: "0.7rem",
                    fontWeight: 600,
                  }}
                >
                  Center face in frame
                </span>
              </div>
            </div>

            {/* Reference Photograph View */}
            <div>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", display: "block", marginBottom: "0.5rem" }}>
                2. Submitted Reference Photograph
              </label>
              <div
                style={{
                  width: "100%",
                  height: "220px",
                  backgroundColor: "#0f172a",
                  borderRadius: "8px",
                  overflow: "hidden",
                  border: "2px solid #334155",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                }}
              >
                <img
                  src={customRefPhoto || referencePhoto}
                  alt="Reference ID"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
                <div
                  style={{
                    position: "absolute",
                    bottom: "8px",
                    display: "flex",
                    gap: "0.5rem",
                  }}
                >
                  <label
                    style={{
                      backgroundColor: "rgba(30, 41, 59, 0.9)",
                      color: "#38bdf8",
                      border: "1px solid #475569",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "0.7rem",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Upload ID Photo
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onloadend = () => setCustomRefPhoto(reader.result as string);
                          reader.readAsDataURL(file);
                        }
                      }}
                    />
                  </label>
                  {customRefPhoto && (
                    <button
                      onClick={() => setCustomRefPhoto(null)}
                      style={{
                        backgroundColor: "rgba(30, 41, 59, 0.9)",
                        color: "#94a3b8",
                        border: "1px solid #475569",
                        padding: "3px 8px",
                        borderRadius: "4px",
                        fontSize: "0.7rem",
                        cursor: "pointer",
                      }}
                    >
                      Reset to Sample
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Hard Gate Rules Box */}
          <div
            style={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              padding: "0.85rem 1rem",
              marginBottom: "1.25rem",
              fontSize: "0.8rem",
              color: "#94a3b8",
              lineHeight: 1.5,
            }}
          >
            <div style={{ color: "#f8fafc", fontWeight: 700, marginBottom: "0.25rem" }}>
              Enforced Security Checks:
            </div>
            <ul style={{ margin: 0, paddingLeft: "1.2rem", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
              <li>Exactly one face must be present in view (zero or multiple faces trigger rejection).</li>
              <li>Live face is matched against reference photograph with multi-metric similarity confidence.</li>
              <li>
                <strong>Pass:</strong> Unlocks reasoning interview chamber • <strong>Fail / Uncertain:</strong> Session is blocked and automatically routed to human committee review.
              </li>
            </ul>
          </div>

          {/* Status Alert if Failed / Uncertain */}
          {identityStatus !== "NOT_VERIFIED" && identityStatus !== "PASS" && (
            <div
              style={{
                backgroundColor: "#881337",
                border: "1px solid #f43f5e",
                color: "#ffe4e6",
                padding: "0.85rem 1rem",
                borderRadius: "8px",
                marginBottom: "1.25rem",
                fontSize: "0.85rem",
              }}
            >
              <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span>⛔ Interview Entry Blocked</span>
                <span style={{ fontSize: "0.75rem", backgroundColor: "#4c0519", padding: "1px 6px", borderRadius: "4px" }}>
                  Status: {identityStatus}
                </span>
              </div>
              <p style={{ margin: "0.4rem 0 0 0", fontSize: "0.8rem", color: "#fecdd3" }}>
                {identityReason || "Face matching confidence insufficient or multiple faces detected. Candidate routed to human review."}
              </p>
            </div>
          )}

          {error && (
            <div
              style={{
                backgroundColor: "#7f1d1d",
                color: "#fca5a5",
                padding: "0.75rem",
                borderRadius: "6px",
                marginBottom: "1rem",
                fontSize: "0.85rem",
              }}
            >
              {error}
            </div>
          )}

          {/* Action Button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              onClick={() => router.push("/student/applications")}
              style={{
                backgroundColor: "#334155",
                color: "#cbd5e1",
                border: "none",
                padding: "0.65rem 1.25rem",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ← Back to Applications
            </button>

            <button
              onClick={handleVerifyIdentity}
              disabled={verifyingIdentity}
              style={{
                backgroundColor: verifyingIdentity ? "#475569" : "#2563eb",
                color: "#ffffff",
                border: "none",
                padding: "0.75rem 1.75rem",
                borderRadius: "6px",
                fontSize: "0.95rem",
                fontWeight: 700,
                cursor: verifyingIdentity ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              {verifyingIdentity ? (
                <>
                  <div className="spinner-small" /> Running Biometric Hard Gate...
                </>
              ) : (
                "Verify Identity & Authenticate (Hard Gate) →"
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // STAGE 4: REASONING VOICE INTERVIEW ROOM
  // -------------------------------------------------------------------------
  return (
    <div
      style={{
        maxWidth: "1280px",
        width: "100%",
        margin: "1rem auto",
        padding: "0 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        height: "calc(100vh - 5.5rem)",
      }}
    >
      {/* Top Session Header */}
      <header
        style={{
          backgroundColor: "#1e293b",
          border: "1px solid #334155",
          borderRadius: "8px",
          padding: "0.85rem 1.25rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "#f8fafc", fontWeight: 700 }}>
              Stage 4: Reasoning AI Voice Interview
            </h2>
            <span
              style={{
                backgroundColor: "#065f46",
                color: "#34d399",
                fontSize: "0.7rem",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "4px",
              }}
            >
              ✓ Identity Gate Verified ({Math.round(identityConfidence * 100)}%)
            </span>
          </div>
          <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>
            {isCompleted
              ? "Interview Finalized"
              : `Dynamic Question Turn ${Math.min(currentQuestionIndex + 1, totalQuestions)} of ${totalQuestions} • Broad Competency Pivots Active`}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {/* TTS Audio Readout Toggle */}
          <button
            onClick={() => {
              setTtsEnabled(!ttsEnabled);
              if (speaking) {
                window.speechSynthesis?.cancel();
                setSpeaking(false);
              }
            }}
            style={{
              backgroundColor: ttsEnabled ? "#1e3a8a" : "#334155",
              color: ttsEnabled ? "#60a5fa" : "#94a3b8",
              border: `1px solid ${ttsEnabled ? "#2563eb" : "#475569"}`,
              padding: "0.4rem 0.75rem",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
          >
            {ttsEnabled ? "🔊 Voice Audio ON" : "🔇 Voice Audio MUTED"}
          </button>

          {proctoringTelemetry.violations_count > 0 && (
            <span
              style={{
                backgroundColor: "#881337",
                color: "#f43f5e",
                padding: "0.25rem 0.6rem",
                borderRadius: "4px",
                fontSize: "0.75rem",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
              }}
            >
              ⚠️ Flagged Alerts: {proctoringTelemetry.violations_count}
            </span>
          )}

          <button
            onClick={() => router.push("/student/applications")}
            style={{
              backgroundColor: "#334155",
              color: "#cbd5e1",
              border: "1px solid #475569",
              padding: "0.4rem 0.8rem",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "0.8rem",
              fontWeight: 600,
            }}
          >
            ← My Applications
          </button>
        </div>
      </header>

      {/* Main Two-Column Layout */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: isCompleted ? "1fr" : "340px 1fr",
          gap: "1rem",
          minHeight: 0,
        }}
      >
        {/* Left Column: Live Webcam Stream & Anti-Swap Proctoring */}
        {!isCompleted && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <VideoProctor
              onTelemetryUpdate={handleTelemetryUpdate}
              isCompleted={isCompleted}
            />

            {/* Candidate Rules & Instructions Card */}
            <div
              style={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                padding: "1rem",
                fontSize: "0.8rem",
                color: "#94a3b8",
                lineHeight: "1.5",
              }}
            >
              <h4 style={{ color: "#f8fafc", margin: "0 0 0.5rem 0", fontSize: "0.85rem" }}>
                🔒 Continuous Proctoring & Voice Rules
              </h4>
              <ul style={{ margin: 0, paddingLeft: "1.2rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                <li>Keep webcam centered — anti-swap verification runs continuously.</li>
                <li>You can answer by speaking into your mic or typing into the text field.</li>
                <li>The AI recognizes emerging competencies (e.g. mentoring, architecture) and dynamically pivots questions.</li>
                <li>
                  <strong style={{ color: "#f43f5e" }}>Single Attempt:</strong> Interview cannot be retaken once concluded.
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Right Column: Active Question, Voice/Text Input, & Transcript */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
            minHeight: 0,
            overflowY: "auto",
            paddingRight: "0.25rem",
          }}
        >
          {error && (
            <div
              style={{
                backgroundColor: "#7f1d1d",
                border: "1px solid #dc2626",
                color: "#fecaca",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                fontSize: "0.85rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>⚠️ {error}</span>
              <button
                type="button"
                onClick={() => setError("")}
                style={{
                  backgroundColor: "transparent",
                  border: "none",
                  color: "#fecaca",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                ✕
              </button>
            </div>
          )}

          {!isCompleted && (
            <>
              {/* 1. PROMINENT CURRENT QUESTION CARD */}
              <div
                style={{
                  backgroundColor: "#1e293b",
                  border: "2px solid #3b82f6",
                  borderRadius: "12px",
                  padding: "1.5rem",
                  boxShadow: "0 10px 25px -5px rgba(59, 130, 246, 0.25)",
                }}
              >
                {/* Header: Turn status & Decision Badge */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1rem",
                    paddingBottom: "0.75rem",
                    borderBottom: "1px solid #334155",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
                    <span
                      style={{
                        backgroundColor: "#1d4ed8",
                        color: "#ffffff",
                        fontWeight: 700,
                        fontSize: "0.8rem",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        letterSpacing: "0.025em",
                      }}
                    >
                      QUESTION {Math.min(currentQuestionIndex + 1, totalQuestions)} OF {totalQuestions}
                    </span>

                    {currentDecision && (
                      <span
                        style={{
                          backgroundColor:
                            currentDecision === "broad_pivot"
                              ? "#581c87"
                              : currentDecision === "narrow_follow_up"
                              ? "#0c4a6e"
                              : currentDecision === "opening_question"
                              ? "#064e3b"
                              : "#1e293b",
                          color:
                            currentDecision === "broad_pivot"
                              ? "#e9d5ff"
                              : currentDecision === "narrow_follow_up"
                              ? "#7dd3fc"
                              : currentDecision === "opening_question"
                              ? "#6ee7b7"
                              : "#94a3b8",
                          border: "1px solid #475569",
                          fontWeight: 700,
                          fontSize: "0.75rem",
                          padding: "3px 8px",
                          borderRadius: "6px",
                          textTransform: "uppercase",
                        }}
                      >
                        {currentDecision === "broad_pivot"
                          ? "🔀 Broad Competency Pivot"
                          : currentDecision === "narrow_follow_up"
                          ? "🎯 Targeted Deep Follow-up"
                          : currentDecision === "opening_question"
                          ? "🌟 Opening Question"
                          : "📋 Competency Assessment"}
                      </span>
                    )}
                  </div>

                  {/* TTS Listen Button */}
                  {activeQuestion && !questionLoading && (
                    <button
                      type="button"
                      onClick={() => speakText(activeQuestion)}
                      style={{
                        backgroundColor: speaking ? "#2563eb" : "#334155",
                        color: "#ffffff",
                        border: "1px solid #475569",
                        borderRadius: "6px",
                        padding: "0.35rem 0.75rem",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.35rem",
                      }}
                    >
                      {speaking ? "🔊 Speaking..." : "🔈 Read Aloud"}
                    </button>
                  )}
                </div>

                {/* Question Body */}
                {questionLoading ? (
                  <div
                    style={{
                      padding: "1.75rem 1rem",
                      textAlign: "center",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "0.75rem",
                    }}
                  >
                    <div className="spinner-large" style={{ borderColor: "#38bdf8", borderTopColor: "transparent" }} />
                    <div style={{ color: "#38bdf8", fontSize: "1.1rem", fontWeight: 600 }}>
                      AI Interviewer is formulating Question {Math.min(currentQuestionIndex + 1, totalQuestions)}...
                    </div>
                    <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                      Semantically deliberating over technical claims, prior answers & evaluation competencies
                    </div>
                  </div>
                ) : activeQuestion ? (
                  <div>
                    <p
                      style={{
                        color: "#f8fafc",
                        fontSize: "1.15rem",
                        fontWeight: 600,
                        lineHeight: "1.6",
                        margin: "0 0 0.5rem 0",
                      }}
                    >
                      {activeQuestion}
                    </p>
                    {latestReasoning && (
                      <div
                        style={{
                          marginTop: "0.75rem",
                          backgroundColor: "rgba(15, 23, 42, 0.6)",
                          borderLeft: "3px solid #38bdf8",
                          padding: "0.4rem 0.75rem",
                          borderRadius: "0 4px 4px 0",
                          fontSize: "0.75rem",
                          color: "#94a3b8",
                        }}
                      >
                        <strong style={{ color: "#7dd3fc" }}>Reasoning: </strong>
                        {latestReasoning}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: "center", padding: "1.5rem", color: "#94a3b8" }}>
                    <p style={{ margin: "0 0 0.75rem 0" }}>Interview session is active. Ready to load question.</p>
                    <button
                      type="button"
                      onClick={() => checkGateAndFetch()}
                      style={{
                        backgroundColor: "#2563eb",
                        color: "#ffffff",
                        border: "none",
                        padding: "0.5rem 1rem",
                        borderRadius: "6px",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                      }}
                    >
                      Load Interview Question
                    </button>
                  </div>
                )}
              </div>

              {/* 2. CANDIDATE ANSWER INPUT CARD */}
              <div
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "12px",
                  padding: "1.25rem",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "0.75rem",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <label style={{ fontSize: "0.9rem", fontWeight: 700, color: "#cbd5e1" }}>
                    Your Technical Answer (Voice or Typed)
                  </label>

                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    {/* Voice Dictation Toggle Button */}
                    <button
                      type="button"
                      onClick={toggleVoiceRecording}
                      disabled={submitting || questionLoading || isCompleted}
                      style={{
                        backgroundColor: isRecording ? "#dc2626" : "#2563eb",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "6px",
                        padding: "0.45rem 0.9rem",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        cursor: submitting || questionLoading ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        boxShadow: isRecording ? "0 0 15px rgba(220, 38, 38, 0.7)" : "none",
                        transition: "all 0.2s ease",
                      }}
                    >
                      {isRecording ? (
                        <>
                          <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ffffff" }} />
                          Recording Voice... (Click to Stop)
                        </>
                      ) : (
                        <>🎙️ Speak Answer (Mic)</>
                      )}
                    </button>

                    {inputValue && (
                      <button
                        type="button"
                        onClick={() => setInputValue("")}
                        disabled={submitting}
                        style={{
                          backgroundColor: "transparent",
                          color: "#94a3b8",
                          border: "1px solid #475569",
                          borderRadius: "6px",
                          padding: "0.45rem 0.75rem",
                          fontSize: "0.8rem",
                          cursor: "pointer",
                        }}
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                {/* Answer Textarea */}
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={submitting || questionLoading || isCompleted}
                  rows={4}
                  placeholder={
                    isRecording
                      ? "Listening to your spoken response in real-time... (speak now into your microphone)"
                      : "Speak using the microphone button above or type your technical answer here..."
                  }
                  style={{
                    width: "100%",
                    backgroundColor: "#0f172a",
                    border: isRecording ? "2px solid #ef4444" : "1px solid #334155",
                    borderRadius: "8px",
                    padding: "0.85rem",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                    lineHeight: "1.5",
                    fontFamily: "inherit",
                    resize: "vertical",
                    boxSizing: "border-box",
                    outline: "none",
                  }}
                />

                {/* Bottom Row: Helpers & Submit Button */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: "0.75rem",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    {inputValue.trim() ? `${inputValue.trim().split(/\s+/).length} words` : "Waiting for response..."} • The AI deliberates on technical depth & trade-offs.
                  </div>

                  <button
                    type="button"
                    onClick={handleSendResponse}
                    disabled={submitting || questionLoading || isCompleted || !inputValue.trim()}
                    style={{
                      backgroundColor: submitting || questionLoading || !inputValue.trim() ? "#334155" : "#10b981",
                      color: "#ffffff",
                      border: "none",
                      borderRadius: "6px",
                      padding: "0.6rem 1.4rem",
                      fontSize: "0.9rem",
                      fontWeight: 700,
                      cursor: submitting || questionLoading || !inputValue.trim() ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                    }}
                  >
                    {submitting ? (
                      <>
                        <div className="spinner-small" /> Reasoning & Evaluating...
                      </>
                    ) : (
                      "Submit Answer →"
                    )}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* 3. INTERVIEW TRANSCRIPT & CONVERSATION HISTORY */}
          <div
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "12px",
              padding: "1rem",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: showHistory ? "0.75rem" : 0,
                cursor: "pointer",
              }}
              onClick={() => setShowHistory(!showHistory)}
            >
              <h4 style={{ margin: 0, fontSize: "0.9rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                📜 Interview Transcript & History ({messages.length} exchanges)
              </h4>
              <span style={{ fontSize: "0.8rem", color: "#38bdf8" }}>
                {showHistory ? "▲ Collapse" : "▼ Expand"}
              </span>
            </div>

            {showHistory && (
              <div
                style={{
                  maxHeight: "350px",
                  overflowY: "auto",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.85rem",
                  paddingRight: "0.25rem",
                }}
              >
                {messages.length === 0 ? (
                  <p style={{ color: "#64748b", fontSize: "0.85rem", margin: 0, textAlign: "center", padding: "1rem 0" }}>
                    No previous exchanges recorded yet.
                  </p>
                ) : (
                  messages.map((msg, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "0.75rem 1rem",
                        borderRadius: "8px",
                        backgroundColor: msg.sender === "CANDIDATE" ? "rgba(37, 99, 235, 0.15)" : "#0f172a",
                        borderLeft: msg.sender === "CANDIDATE" ? "3px solid #2563eb" : "3px solid #10b981",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "0.35rem",
                          fontSize: "0.75rem",
                          color: msg.sender === "CANDIDATE" ? "#93c5fd" : "#6ee7b7",
                          fontWeight: 700,
                        }}
                      >
                        <span>{msg.sender === "CANDIDATE" ? "You (Candidate)" : "🤖 AI Interviewer"}</span>
                        {msg.turn_score !== undefined && msg.turn_score !== null && (
                          <span
                            style={{
                              backgroundColor: msg.turn_score >= 70 ? "#065f46" : "#78350f",
                              color: msg.turn_score >= 70 ? "#34d399" : "#fbbf24",
                              padding: "1px 6px",
                              borderRadius: "4px",
                            }}
                          >
                            Turn Score: {msg.turn_score}/100
                          </span>
                        )}
                      </div>

                      <div style={{ color: "#e2e8f0", fontSize: "0.88rem", lineHeight: "1.5", whiteSpace: "pre-wrap" }}>
                        {msg.content}
                      </div>

                      {/* Reasoning Log display if present */}
                      {msg.turn_feedback?.reasoning && (
                        <div
                          style={{
                            marginTop: "0.4rem",
                            backgroundColor: "rgba(15, 23, 42, 0.8)",
                            padding: "0.35rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.72rem",
                            color: "#94a3b8",
                          }}
                        >
                          <span style={{ color: "#f59e0b", fontWeight: 700 }}>
                            Decision: {msg.turn_feedback.decision?.toUpperCase() || "EVALUATED"} •{" "}
                          </span>
                          {msg.turn_feedback.reasoning}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* 4. STAGE 5 FINAL EVALUATION REPORT CARD (when isCompleted) */}
          {isCompleted && finalReport && (
            <div
              style={{
                backgroundColor: "#1e293b",
                border: `2px solid ${
                  finalReport.recommendation === "RECOMMENDED"
                    ? "#10b981"
                    : finalReport.recommendation === "BORDERLINE"
                    ? "#f59e0b"
                    : "#ef4444"
                }`,
                borderRadius: "12px",
                padding: "1.5rem",
                boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
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
                <h3 style={{ margin: 0, color: "#f8fafc", fontSize: "1.25rem" }}>
                  🎓 Stage 5 Final Evaluation & Recommendation
                </h3>
                <span
                  style={{
                    backgroundColor:
                      finalReport.recommendation === "RECOMMENDED"
                        ? "#065f46"
                        : finalReport.recommendation === "BORDERLINE"
                        ? "#78350f"
                        : "#881337",
                    color:
                      finalReport.recommendation === "RECOMMENDED"
                        ? "#34d399"
                        : finalReport.recommendation === "BORDERLINE"
                        ? "#fbbf24"
                        : "#f43f5e",
                    padding: "0.35rem 0.85rem",
                    borderRadius: "9999px",
                    fontSize: "0.85rem",
                    fontWeight: 700,
                  }}
                >
                  {finalReport.recommendation}
                </span>
              </div>

              {/* Stage 5 Composite Score Calculation Box */}
              {finalReport.stage5_composite && (
                <div
                  style={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "1rem",
                    marginBottom: "1rem",
                    display: "flex",
                    justifyContent: "space-around",
                    alignItems: "center",
                  }}
                >
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Stage 1 Resume (40%)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#38bdf8" }}>
                      {finalReport.stage5_composite.resume_score}/100
                    </div>
                  </div>
                  <div style={{ color: "#64748b", fontSize: "1.2rem" }}>+</div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Stage 4 Interview (60%)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#a855f7" }}>
                      {finalReport.stage5_composite.interview_score}/100
                    </div>
                  </div>
                  <div style={{ color: "#64748b", fontSize: "1.2rem" }}>=</div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: 700 }}>Stage 5 Composite Score</div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#10b981" }}>
                      {finalReport.stage5_composite.composite_score}/100
                    </div>
                  </div>
                </div>
              )}

              <p style={{ color: "#e2e8f0", fontSize: "0.9rem", lineHeight: "1.6", marginBottom: "1rem" }}>
                {finalReport.summary_reasoning}
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.85rem" }}>
                <div>
                  <h4 style={{ color: "#34d399", margin: "0 0 0.5rem 0" }}>Key Strengths</h4>
                  <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#cbd5e1" }}>
                    {finalReport.strengths?.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 style={{ color: "#fbbf24", margin: "0 0 0.5rem 0" }}>Areas for Improvement</h4>
                  <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#cbd5e1" }}>
                    {finalReport.weaknesses?.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div style={{ marginTop: "1.5rem", borderTop: "1px solid #334155", paddingTop: "1rem" }}>
                <button
                  type="button"
                  onClick={() => router.push("/student/applications")}
                  style={{
                    backgroundColor: "#2563eb",
                    color: "#ffffff",
                    border: "none",
                    padding: "0.5rem 1.25rem",
                    borderRadius: "6px",
                    fontWeight: 600,
                    cursor: "pointer",
                    fontSize: "0.9rem",
                  }}
                >
                  Return to My Applications
                </button>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>
    </div>
  );
}
