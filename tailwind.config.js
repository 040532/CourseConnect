/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./frontend/src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        parchment: "#f5f1e8",
        ink: "#172033",
        slate: "#4f6273",
        accent: "#ad7c2f",
        evergreen: "#1d5f53",
        roseclay: "#965f5a",
        mist: "#dde6e3",
      },
      boxShadow: {
        panel: "0 20px 45px -24px rgba(23, 32, 51, 0.35)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      backgroundImage: {
        grain:
          "radial-gradient(circle at 25% 20%, rgba(173, 124, 47, 0.18), transparent 0 24%), radial-gradient(circle at 80% 10%, rgba(29, 95, 83, 0.16), transparent 0 20%), radial-gradient(circle at 50% 80%, rgba(150, 95, 90, 0.14), transparent 0 18%)",
      },
    },
  },
  plugins: [],
};
