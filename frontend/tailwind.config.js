/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-canvas)",
        surface: {
          DEFAULT: "var(--color-surface)",
          raised: "var(--color-surface-raised)",
          hover: "var(--color-surface-hover)",
          active: "var(--color-surface-active)",
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
          950: "#080c14",
        },
        border: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
        },
        signal: {
          DEFAULT: "var(--color-signal)",
          subtle: "var(--color-signal-subtle)",
        },
        evidence: {
          DEFAULT: "var(--color-evidence)",
          subtle: "var(--color-evidence-subtle)",
        },
        artifact: {
          DEFAULT: "var(--color-artifact)",
          subtle: "var(--color-artifact-subtle)",
        },
        danger: {
          DEFAULT: "var(--color-danger)",
          subtle: "var(--color-danger-subtle)",
        },
        content: {
          DEFAULT: "var(--color-text)",
          muted: "var(--color-text-muted)",
          subtle: "var(--color-text-subtle)",
        },
        brand: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
          950: "#052e16",
          DEFAULT: "var(--color-signal)",
        },
        accent: {
          amber: "#f59e0b",
          cyan: "#06b6d4",
          purple: "#8b5cf6",
        },
      },
      fontFamily: {
        serif: [
          '"Newsreader"',
          '"Charter"',
          '"Georgia"',
          '"Cambria"',
          '"Times New Roman"',
          "serif",
        ],
        sans: [
          '"Inter"',
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          "sans-serif",
        ],
        mono: [
          '"JetBrains Mono"',
          '"Fira Code"',
          "Consolas",
          "monospace",
        ],
      },
      animation: {
        "pulse-subtle": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.2s ease-out forwards",
        "slide-up": "slideUp 0.2s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
