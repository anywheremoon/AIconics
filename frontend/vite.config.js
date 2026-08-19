//C 테스트용으로 임시로 제작함
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    proxy: apiProxy,
  },

  preview: {
    proxy: apiProxy,
  },
});
