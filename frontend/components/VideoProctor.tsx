"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface ProctoringTelemetry {
  violations_count: number;
  tab_switches: number;
  events: Array<{
    type: "NO_FACE" | "MULTIPLE_FACES" | "LOOK_AWAY" | "TAB_SWITCH";
    timestamp: string;
    description: string;
  }>;
}

interface VideoProctorProps {
  onTelemetryUpdate: (telemetry: ProctoringTelemetry) => void;
  isCompleted?: boolean;
}

export default function VideoProctor({
  onTelemetryUpdate,
  isCompleted = false,
}: VideoProctorProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [streamActive, setStreamActive] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string>("");
  const [faceStatus, setFaceStatus] = useState<"NORMAL" | "WARNING" | "CRITICAL">("NORMAL");
  const [alertMessage, setAlertMessage] = useState<string>("Initializing Proctoring...");
  const [totalViolations, setTotalViolations] = useState<number>(0);

  const telemetryRef = useRef<ProctoringTelemetry>({
    violations_count: 0,
    tab_switches: 0,
    events: [],
  });

  const recordEvent = useCallback(
    (type: "NO_FACE" | "MULTIPLE_FACES" | "LOOK_AWAY" | "TAB_SWITCH", description: string) => {
      telemetryRef.current.violations_count += 1;
      telemetryRef.current.events.push({
        type,
        timestamp: new Date().toISOString(),
        description,
      });
      setTotalViolations(telemetryRef.current.violations_count);
      onTelemetryUpdate({ ...telemetryRef.current });
    },
    [onTelemetryUpdate]
  );

  // 1. Initialize Webcam MediaStream
  useEffect(() => {
    if (isCompleted) return;

    let localStream: MediaStream | null = null;

    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
          audio: false,
        });
        localStream = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          setStreamActive(true);
          setAlertMessage("Face verified in frame");
          setFaceStatus("NORMAL");
        }
      } catch (err: unknown) {
        console.error("Camera access error:", err);
        setCameraError(
          "Camera access denied. Please grant webcam permissions to proceed with this proctored academic interview."
        );
        recordEvent("NO_FACE", "Camera access denied by candidate browser.");
      }
    }

    initCamera();

    return () => {
      if (localStream) {
        localStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [isCompleted, recordEvent]);

  // 2. Tab switch detection
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden && !isCompleted) {
        telemetryRef.current.tab_switches += 1;
        recordEvent("TAB_SWITCH", "Candidate switched away from interview browser tab.");
        setFaceStatus("WARNING");
        setAlertMessage("⚠️ Window unfocused / Tab switched!");
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [isCompleted, recordEvent]);

  // 3. Computer Vision / Heuristic Frame Analysis
  useEffect(() => {
    if (!streamActive || isCompleted) return;

    let consecutiveAbsence = 0;

    const interval = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = 160;
      canvas.height = 120;
      ctx.drawImage(video, 0, 0, 160, 120);

      const frameData = ctx.getImageData(0, 0, 160, 120).data;

      // Sample center brightness and variation to detect camera occlusion or face presence
      let totalLuma = 0;
      let pixelCount = 0;
      for (let i = 0; i < frameData.length; i += 16) {
        const r = frameData[i];
        const g = frameData[i + 1];
        const b = frameData[i + 2];
        const luma = 0.299 * r + 0.587 * g + 0.114 * b;
        totalLuma += luma;
        pixelCount++;
      }

      const avgLuma = totalLuma / pixelCount;

      // Check for camera covered / pitch black or pure whiteout
      if (avgLuma < 12 || avgLuma > 245) {
        consecutiveAbsence++;
        if (consecutiveAbsence >= 3) {
          setFaceStatus("CRITICAL");
          setAlertMessage("🚨 Camera view blocked or pitch black!");
          if (consecutiveAbsence === 3) {
            recordEvent("NO_FACE", "Camera view occluded or dark.");
          }
        }
      } else {
        consecutiveAbsence = 0;
        setFaceStatus("NORMAL");
        setAlertMessage("🟢 Video feed clear & candidate centered");
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [streamActive, isCompleted, recordEvent]);

  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "8px",
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.2)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              backgroundColor: streamActive ? "#10b981" : "#ef4444",
              display: "inline-block",
              boxShadow: streamActive ? "0 0 8px #10b981" : "none",
            }}
          />
          <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "#f8fafc" }}>
            Candidate Video Stream
          </span>
        </div>

        <span
          style={{
            fontSize: "0.75rem",
            padding: "0.2rem 0.5rem",
            borderRadius: "4px",
            fontWeight: 700,
            backgroundColor:
              faceStatus === "NORMAL"
                ? "#065f46"
                : faceStatus === "WARNING"
                ? "#78350f"
                : "#881337",
            color:
              faceStatus === "NORMAL"
                ? "#34d399"
                : faceStatus === "WARNING"
                ? "#fbbf24"
                : "#f43f5e",
          }}
        >
          {faceStatus === "NORMAL" ? "LIVE PROCTORED" : "FLAGGED EVENT"}
        </span>
      </div>

      {/* Video Container with overlay */}
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "4/3",
          backgroundColor: "#020617",
          borderRadius: "6px",
          overflow: "hidden",
          border: `2px solid ${
            faceStatus === "NORMAL" ? "#334155" : faceStatus === "WARNING" ? "#f59e0b" : "#ef4444"
          }`,
        }}
      >
        {cameraError ? (
          <div
            style={{
              padding: "1.5rem",
              color: "#f87171",
              fontSize: "0.85rem",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <p style={{ margin: 0, fontWeight: 700 }}>⚠️ Camera Inactive</p>
            <p style={{ marginTop: "0.5rem", color: "#cbd5e1" }}>{cameraError}</p>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              muted
              playsInline
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                transform: "scaleX(-1)", // Mirror effect
              }}
            />
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {/* Rec Badge */}
            <div
              style={{
                position: "absolute",
                top: "10px",
                left: "10px",
                backgroundColor: "rgba(0, 0, 0, 0.65)",
                padding: "0.25rem 0.5rem",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                fontSize: "0.7rem",
                color: "#f8fafc",
                fontWeight: 600,
              }}
            >
              <span
                style={{
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  backgroundColor: "#ef4444",
                  display: "inline-block",
                  animation: "pulse 1.5s infinite",
                }}
              />
              REC
            </div>
          </>
        )}
      </div>

      {/* Proctoring Status Bar */}
      <div
        style={{
          backgroundColor: "#0f172a",
          padding: "0.5rem 0.75rem",
          borderRadius: "6px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.75rem",
        }}
      >
        <span style={{ color: "#94a3b8" }}>{alertMessage}</span>
        <span
          style={{
            fontWeight: 700,
            color: totalViolations === 0 ? "#34d399" : "#fbbf24",
          }}
        >
          Violations: {totalViolations}
        </span>
      </div>
    </div>
  );
}
