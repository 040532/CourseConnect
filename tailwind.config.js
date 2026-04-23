/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./frontend/src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "tamu-page": "#f8f4ef",
        "tamu-cream": "#f5ede0",
        "tamu-stone": "#e8ddd0",
        "tamu-maroon": "#500000",
        "tamu-maroon-dark": "#3a0000",
        "tamu-gold": "#d6b35f",
        "tamu-gold-dark": "#8b6b2e",
        "tamu-brick": "#8a4b4b",
        "tamu-ink": "#201716",
        "tamu-slate": "#685c58",
        "tamu-muted": "#8b7d78",
      },
      boxShadow: {
        panel: "0 22px 48px -24px rgba(80, 0, 0, 0.28)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
};
