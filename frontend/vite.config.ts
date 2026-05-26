import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const allowedHosts = [
  "rolling-cite-souls-dictionary.trycloudflare.com",
  ...(process.env.VITE_ALLOWED_HOSTS?.split(",").map((host) => host.trim()).filter(Boolean) ?? [])
];

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts,
    port: 5173
  }
});
