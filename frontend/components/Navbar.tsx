"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();

  const [role, setRole] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const storedRole = localStorage.getItem("role");
    const storedName = localStorage.getItem("name");

    if (token) {
      setIsLoggedIn(true);
      setRole(storedRole);
      setUserName(storedName || (storedRole === "teacher" ? "Faculty" : "Student"));
    } else {
      setIsLoggedIn(false);
      setRole(null);
      setUserName(null);
    }
  }, [pathname]);

  // Do not render navbar on the login/register landing page
  if (pathname === "/" || !isLoggedIn) {
    return null;
  }

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");
    localStorage.removeItem("name");
    localStorage.removeItem("user_id");
    setIsLoggedIn(false);
    router.push("/");
  };

  const isTeacher = role === "teacher";

  return (
    <nav
      style={{
        backgroundColor: "#0f172a",
        borderBottom: "1px solid #334155",
        padding: "0.75rem 1.5rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 100,
        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
      }}
    >
      {/* Brand / Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
        <Link
          href={isTeacher ? "/teacher/dashboard" : "/student/openings"}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            textDecoration: "none",
            color: "#f8fafc",
            fontWeight: 800,
            fontSize: "1.1rem",
            letterSpacing: "-0.02em",
          }}
        >
          <span
            style={{
              backgroundColor: "#2563eb",
              color: "#ffffff",
              padding: "0.25rem 0.6rem",
              borderRadius: "6px",
              fontSize: "0.9rem",
            }}
          >
            🎓 AIA
          </span>
          <span>Academic Interview Agent</span>
        </Link>

        {/* Navigation Links */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {isTeacher ? (
            <>
              <Link
                href="/teacher/dashboard"
                style={{
                  color: pathname.includes("/teacher/dashboard") ? "#38bdf8" : "#94a3b8",
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  padding: "0.35rem 0.6rem",
                  borderRadius: "4px",
                  transition: "color 0.2s",
                }}
              >
                Dashboard
              </Link>
              <Link
                href="/teacher/create-opening"
                style={{
                  color: pathname.includes("/teacher/create-opening") ? "#38bdf8" : "#94a3b8",
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  padding: "0.35rem 0.6rem",
                  borderRadius: "4px",
                  transition: "color 0.2s",
                }}
              >
                + Create Opening
              </Link>
            </>
          ) : (
            <>
              <Link
                href="/student/openings"
                style={{
                  color: pathname.includes("/student/openings") ? "#38bdf8" : "#94a3b8",
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  padding: "0.35rem 0.6rem",
                  borderRadius: "4px",
                  transition: "color 0.2s",
                }}
              >
                Browse Openings
              </Link>
              <Link
                href="/student/applications"
                style={{
                  color: pathname.includes("/student/applications") ? "#38bdf8" : "#94a3b8",
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  padding: "0.35rem 0.6rem",
                  borderRadius: "4px",
                  transition: "color 0.2s",
                }}
              >
                My Applications
              </Link>
            </>
          )}
        </div>
      </div>

      {/* User Info & Logout */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span
            style={{
              backgroundColor: isTeacher ? "#065f46" : "#1e3a8a",
              color: isTeacher ? "#34d399" : "#60a5fa",
              border: `1px solid ${isTeacher ? "#059669" : "#2563eb"}`,
              padding: "0.2rem 0.6rem",
              borderRadius: "9999px",
              fontSize: "0.75rem",
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            {isTeacher ? "Faculty" : "Student"}
          </span>
          <span style={{ color: "#e2e8f0", fontSize: "0.9rem", fontWeight: 600 }}>
            {userName}
          </span>
        </div>

        <button
          onClick={handleLogout}
          style={{
            backgroundColor: "#334155",
            color: "#cbd5e1",
            border: "1px solid #475569",
            padding: "0.35rem 0.85rem",
            borderRadius: "6px",
            fontSize: "0.85rem",
            fontWeight: 600,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#dc2626";
            e.currentTarget.style.color = "#ffffff";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#334155";
            e.currentTarget.style.color = "#cbd5e1";
          }}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
