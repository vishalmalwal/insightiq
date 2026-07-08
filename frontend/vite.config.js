var _a;
/// <reference types="node" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
// Dev proxy: forward /api to the FastAPI backend to avoid CORS in local dev.
export default defineConfig({
    plugins: [react()],
    build: {
        chunkSizeWarningLimit: 600,
        rollupOptions: {
            output: {
                manualChunks: {
                    echarts: ["echarts"],
                    grid: ["react-grid-layout"],
                    motion: ["framer-motion", "lenis"],
                },
            },
        },
    },
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: (_a = process.env.VITE_API_TARGET) !== null && _a !== void 0 ? _a : "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
    test: {
        environment: "jsdom",
        globals: true,
        setupFiles: "./src/test/setup.ts",
    },
});
