import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // generateSW avoids the Vite-6 injectManifest custom-SW build that hangs
      // indefinitely on "Building src/sw.ts service worker".
      strategies: "generateSW",
      registerType: "autoUpdate",
      workbox: {
        // development mode skips terser minify (needs global crypto; Node 18 lacks it).
        mode: "development",
        globPatterns: ["**/*.{js,css,html,ico,png,svg,webmanifest}"],
        importScripts: ["sw-push.js"],
      },
      manifest: {
        name: "FS-Corporation CEO Companion",
        short_name: "FS-Corp",
        description: "Mobile CEO dashboard for FS-Corporation",
        theme_color: "#111111",
        background_color: "#111111",
        display: "standalone",
        start_url: "/",
      },
    }),
  ],
  server: { port: 5173 },
});
