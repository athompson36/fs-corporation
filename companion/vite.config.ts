import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
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
