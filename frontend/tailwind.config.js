/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--canvas) / <alpha-value>)",
        ink: "rgb(var(--text) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        // Signature aurora stops — used sparingly (hero, ask-bar, KPI accents).
        accent: "#7C3AED",
        violet: "#7C3AED",
        cyan: "#06B6D4",
        fuchsia: "#D946EF",
      },
      fontFamily: {
        display: ['"Clash Display"', '"General Sans"', "Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        glass: "0 1px 0 0 rgb(255 255 255 / 0.04) inset, 0 8px 40px -12px rgb(0 0 0 / 0.5)",
      },
    },
  },
  plugins: [],
};
