import { useEffect, useState } from "react";
import type { ThemeMode } from "../lib/theme";

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", mode === "dark");
    try {
      localStorage.setItem("insightiq-theme", mode);
    } catch {
      /* storage unavailable — non-fatal */
    }
  }, [mode]);
  return { mode, toggle: () => setMode((m) => (m === "dark" ? "light" : "dark")) };
}
