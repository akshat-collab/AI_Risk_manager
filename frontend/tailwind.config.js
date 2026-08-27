/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070d",
          900: "#070b16",
          800: "#0c1222",
          700: "#121a2e",
        },
        neon: {
          cyan: "#22d3ee",
          mint: "#34d399",
          amber: "#fbbf24",
          orange: "#fb923c",
          rose: "#fb7185",
        },
      },
      fontFamily: {
        sans: ["DM Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(34, 211, 238, 0.12)",
        card: "0 18px 50px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(148,163,184,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.06) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
