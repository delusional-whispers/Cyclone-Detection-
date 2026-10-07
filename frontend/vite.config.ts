import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 43127,
    strictPort: true,
    allowedHosts: true,
    hmr: false,
    cors: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:43128",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 43127,
  },
});
