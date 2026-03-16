"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

type ActiveTheme = "light" | "dark";

function resolveTheme(theme: "system" | "light" | "dark"): ActiveTheme {
  if (theme === "light" || theme === "dark") return theme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: "system" | "light" | "dark"): ActiveTheme {
  const resolved = resolveTheme(theme);
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
  return resolved;
}

export default function ThemeToggle() {
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const [activeTheme, setActiveTheme] = useState<ActiveTheme>("light");

  useEffect(() => {
    setActiveTheme(applyTheme(theme));

    if (theme !== "system") return;

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => setActiveTheme(applyTheme("system"));
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, [theme]);

  const isDark = activeTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="theme-toggle"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
    >
      <span className="theme-toggle__icon" aria-hidden="true">
        {isDark ? "☀" : "☾"}
      </span>
      <span className="theme-toggle__label">{isDark ? "Light" : "Dark"}</span>
    </button>
  );
}
