import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API lives on the FastAPI server; proxying /api keeps the
// browser on a single origin, exactly like the packaged application.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});