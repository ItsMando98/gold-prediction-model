"use client";

import { useEffect, useState } from "react";

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M8 1v1.4M8 13.6V15M15 8h-1.4M2.4 8H1M12.7 3.3l-1 1M4.3 11.7l-1 1M12.7 12.7l-1-1M4.3 4.3l-1-1"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M13.5 9.8A5.8 5.8 0 116.2 2.5a4.6 4.6 0 007.3 7.3z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Resolves the theme actually painted right now: an explicit stored choice
 * wins, otherwise the OS preference (mirroring the CSS in globals.css). */
function resolveIsDark(): boolean {
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem("theme");
  } catch {
    // localStorage unavailable (private browsing, etc.)
  }
  if (stored === "light") return false;
  if (stored === "dark") return true;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setMounted(true);
    setIsDark(resolveIsDark());

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setIsDark(resolveIsDark());
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  function toggle() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    try {
      window.localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      // ignore
    }
  }

  if (!mounted) {
    return <button className="theme-toggle" aria-hidden="true" style={{ visibility: "hidden" }} />;
  }

  return (
    <button className="theme-toggle" onClick={toggle} aria-label="Toggle color theme">
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
