import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const backend = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

// The backend generates these two from the brand pack at runtime. Adding the
// tags after Vite has processed the page stops it looking for them at build time.
const brandLinks: Plugin = {
  name: "release-radar-brand-links",
  transformIndexHtml: {
    order: "post",
    handler: () => [
      {
        tag: "link",
        attrs: { rel: "stylesheet", href: "/brand/theme.css" },
        injectTo: "head",
      },
      { tag: "link", attrs: { rel: "icon", href: "/brand/favicon" }, injectTo: "head" },
    ],
  },
};

export default defineConfig({
  plugins: [react(), brandLinks],
  server: {
    host: true,
    port: 5173,
    // File-change events do not cross every VM's shared folder (Colima's, for one).
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
    proxy: {
      "/api": backend,
      "/brand": backend,
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // Inlined assets would need data: URIs, which the content security policy
    // does not allow for fonts.
    assetsInlineLimit: 0,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
});
