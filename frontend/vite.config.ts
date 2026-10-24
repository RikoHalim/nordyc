import { defineConfig, loadEnv, normalizePath } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const port = Number(env.FRONTEND_PORT || 5173);
  const target = env.BACKEND_ORIGIN || "http://127.0.0.1:8000";
  const url = new URL(target);
  if (
    !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
    url.protocol !== "http:"
  ) {
    throw new Error(
      "The development API proxy requires an explicit loopback HTTP backend.",
    );
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error("Invalid frontend port.");
  return {
    plugins: [react()],
    server: {
      host: env.FRONTEND_HOST || "127.0.0.1",
      port,
      strictPort: true,
      allowedHosts: env.REPLIT_DEV_DOMAIN ? [env.REPLIT_DEV_DOMAIN] : [],
      fs: {
        strict: true,
        allow: [
          normalizePath(resolve(fileURLToPath(new URL(".", import.meta.url)))),
        ],
        deny: [
          "**/.env",
          "**/.env.*",
          "**/*.{crt,pem,key,p12,pfx}",
          "**/.git/**",
          `${normalizePath(resolve(fileURLToPath(new URL("../data/local", import.meta.url))))}/**`,
          "**/secrets/**",
          "**/*.private.json",
          "**/test-results/**",
          "**/playwright-report/**",
          "**/tests/**",
        ],
      },
      proxy: { "/api": { target }, "/health": { target } },
    },
    preview: { host: "127.0.0.1", port, strictPort: true },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 400,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "react-runtime",
                test: /node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/,
                priority: 20,
              },
              {
                name: "schema-validation",
                test: /node_modules[\\/](ajv|ajv-formats|fast-uri|fast-deep-equal|json-schema-traverse)[\\/]/,
                priority: 15,
              },
              {
                name: "api-contract",
                test: /api[\\/]openapi\.json$/,
                priority: 10,
              },
            ],
          },
        },
      },
    },
  };
});
