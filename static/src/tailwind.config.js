/**
 * Configuración de Tailwind CSS para QA TestBoard.
 * Compilar (desde la raíz del proyecto):
 *   npx tailwindcss@3 -c static/src/tailwind.config.js -i static/src/input.css -o static/css/tailwind.css --minify
 */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#1E2D40", 700: "#2A3D55", 900: "#192734" },
        mint: { DEFAULT: "#2ECC71", 600: "#27B864", 50: "#E6F8EE" },
        passed: { DEFAULT: "#1A7F4B", soft: "#E3F4EA" },
        failed: { DEFAULT: "#D92D45", soft: "#FCE8EB" },
        blocked: { DEFAULT: "#F0BE2C", soft: "#FDF4D9", ink: "#7A5A00" },
        untested: { DEFAULT: "#AEB8C6", soft: "#EEF1F5", ink: "#475569" },
        page: "#F5F7FA",
        line: "#E2E8F0",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
